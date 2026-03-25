from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from ..models import Alerte, IndicateurCache
from ..services.donnees_service import get_prix_actuel
from ..services.telegram_service import send_alert, formater_alerte


def evaluer_alerte(alerte, prix_actuel):
    t = alerte.type_alerte
    if t == Alerte.TYPE_PRIX_HAUT:
        return alerte.seuil and prix_actuel >= float(alerte.seuil)
    if t == Alerte.TYPE_PRIX_BAS:
        return alerte.seuil and prix_actuel <= float(alerte.seuil)
    if t in (Alerte.TYPE_RSI_HAUT, Alerte.TYPE_RSI_BAS):
        indic = IndicateurCache.objects.filter(action=alerte.action).order_by('-date').first()
        if not indic or not indic.rsi_14:
            return False
        rsi = float(indic.rsi_14)
        return rsi > 70 if t == Alerte.TYPE_RSI_HAUT else rsi < 30
    if t == Alerte.TYPE_MACD:
        indic = IndicateurCache.objects.filter(action=alerte.action).order_by('-date').first()
        if not indic or not indic.macd or not indic.macd_signal:
            return False
        return float(indic.macd) > float(indic.macd_signal)
    return False


def envoyer_email_alerte(alerte, prix_actuel, msg_texte):
    """Envoie un email HTML formaté pour une alerte déclenchée."""
    if not alerte.user.email:
        return

    sujet = f'BourseAI — Alerte {alerte.action.symbole}'

    corps_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
                background:#0F1424;color:#E2E8F0;padding:28px;border-radius:12px;">

        <div style="text-align:center;margin-bottom:20px;">
            <h1 style="color:#3B82F6;font-size:22px;margin:0;">Bourse<span style="color:#10D982">AI</span></h1>
            <p style="color:#94A3B8;font-size:12px;margin:4px 0 0;">Notification d'alerte automatique</p>
        </div>

        <div style="background:#151C30;border-radius:10px;padding:20px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                <span style="color:#94A3B8;font-size:13px;">Action</span>
                <span style="color:#3B82F6;font-weight:700;font-size:16px;">{alerte.action.symbole}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                <span style="color:#94A3B8;font-size:13px;">Type d'alerte</span>
                <span style="font-size:13px;">{alerte.get_type_alerte_display()}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                <span style="color:#94A3B8;font-size:13px;">Prix actuel</span>
                <span style="color:#10D982;font-weight:700;font-size:18px;">{prix_actuel:.2f} $</span>
            </div>
            {"<div style='display:flex;justify-content:space-between;margin-bottom:12px;'><span style='color:#94A3B8;font-size:13px;'>Seuil défini</span><span style='font-size:13px;'>" + str(alerte.seuil) + " $</span></div>" if alerte.seuil else ""}
            {"<div style='background:rgba(59,130,246,0.1);border-radius:6px;padding:10px;margin-top:8px;font-size:13px;color:#94A3B8;'>" + alerte.message_perso + "</div>" if alerte.message_perso else ""}
        </div>

        <div style="text-align:center;margin-top:20px;">
            <a href="http://localhost:8000/actions/{alerte.action.symbole}/"
               style="background:#3B82F6;color:white;padding:10px 24px;border-radius:8px;
                      text-decoration:none;font-size:13px;font-weight:600;">
                Analyser {alerte.action.symbole} →
            </a>
        </div>

        <hr style="border:1px solid rgba(99,120,190,0.15);margin:20px 0;">
        <p style="font-size:11px;color:#4A5578;text-align:center;margin:0;">
            BourseAI · Plateforme d'analyse boursière · Alerte créée le {alerte.date_creation.strftime('%d/%m/%Y')}
        </p>
    </div>
    """

    try:
        send_mail(
            subject      = sujet,
            message      = msg_texte,
            from_email   = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [alerte.user.email],
            html_message = corps_html,
            fail_silently= False,
        )
        print(f'[Email] Envoyé à {alerte.user.email}')
    except Exception as e:
        print(f'[Email] Erreur : {e}')


@shared_task(name='bourse.tasks.check_alertes.verifier_alertes')
def verifier_alertes():
    alertes    = Alerte.objects.filter(active=True).select_related('user__profile', 'action')
    declenchees = 0

    for alerte in alertes:
        try:
            prix = get_prix_actuel(alerte.action.symbole)
            if prix is None:
                continue
            if not evaluer_alerte(alerte, prix):
                continue

            msg = formater_alerte(
                symbole      = alerte.action.symbole,
                prix         = prix,
                type_alerte  = alerte.type_alerte,
                seuil        = alerte.seuil,
                message_perso= alerte.message_perso,
            )

            # Notification Telegram
            if alerte.notif_telegram:
                profile = getattr(alerte.user, 'profile', None)
                if profile and profile.telegram_chat_id:
                    send_alert(profile.telegram_chat_id, msg)

            # Notification Email
            if alerte.notif_email:
                envoyer_email_alerte(alerte, prix, msg.replace('<b>', '').replace('</b>', ''))

            # Mettre à jour l'alerte
            alerte.date_declenchement = timezone.now()
            if alerte.desactiver_apres:
                alerte.active = False
            alerte.save(update_fields=['active', 'date_declenchement'])
            declenchees += 1

        except Exception as e:
            print(f'[Alerte] Erreur sur {alerte}: {e}')
            continue

    return f'{declenchees} alerte(s) déclenchée(s)'


@shared_task(name='bourse.tasks.check_alertes.rafraichir_cache_prix')
def rafraichir_cache_prix():
    from ..models import Action
    actions = Action.objects.filter(actif=True)
    for action in actions:
        try:
            get_prix_actuel(action.symbole)
        except Exception:
            pass
    return f'{actions.count()} prix rafraîchis'