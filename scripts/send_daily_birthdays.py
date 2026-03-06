#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, date
from zoneinfo import ZoneInfo
from urllib import request, parse

# Caminho do arquivo com os aniversariantes
DATA_BIRTHDAYS = "data/aniversariantes.json"

# Caminho do arquivo de log de notificações
DATA_LOG = "data/notification_log.json"

# Fuso horário que queremos usar como referência de "hoje"
FORTALEZA_TZ = "America/Fortaleza"


def load_json(path: str, default):
    """Carrega JSON do disco. Se não existir, retorna 'default'."""
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj):
    """Salva um objeto Python em JSON. Cria a pasta automaticamente, se necessário."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def is_leap_year(year: int) -> bool:
    """Retorna True se o ano for bissexto."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def today_in_fortaleza() -> date:
    """Retorna a data de hoje no fuso de Fortaleza."""
    now_fortaleza = datetime.now(ZoneInfo(FORTALEZA_TZ))
    return now_fortaleza.date()


def build_message(person: dict) -> str:
    """Monta a mensagem final do Telegram."""
    name = person.get("name", "").strip()
    desc = person.get("description", "").strip()
    return f"🎉 Hoje é aniversário de {name} — {desc}"


def telegram_send_message(bot_token: str, chat_id: str, text: str) -> None:
    """
    Envia mensagem pelo Telegram.
    Lança exceção se der erro HTTP ou resposta inesperada.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # payload padrão do Telegram
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    data = parse.urlencode(payload).encode("utf-8")

    req = request.Request(url, data=data, method="POST")
    with request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
        # Se quiser, poderia validar o "ok": true do JSON do Telegram
        # mas o status HTTP 200 já é uma boa indicação
        if resp.status != 200:
            raise RuntimeError(f"Telegram HTTP {resp.status}: {body}")


def main():
    # Ler secrets do ambiente
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("ERROR: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.")
        sys.exit(1)

    # Descobre a data "de hoje" no fuso estabelecido
    today = today_in_fortaleza()
    today_str = today.isoformat()

    print(f"[INFO] Today (Fortaleza): {today_str}")

    # Carrega aniversariantes e log
    birthdays = load_json(DATA_BIRTHDAYS, default=[])
    log = load_json(DATA_LOG, default=[])

    # Monta índice para idempotência: (aniversariante_id + notified_date)
    sent_keys = set()
    for entry in log:
        key = f"{entry.get('aniversariante_id')}|{entry.get('notified_date')}"
        sent_keys.add(key)

    # Filtra aniversariantes ativos
    active_birthdays = [p for p in birthdays if p.get("active", True) is True]

    # Seleciona aniversariantes do dia
    today_day = today.day
    today_month = today.month

    todays_people = []
    for p in active_birthdays:
        if p.get("day") == today_day and p.get("month") == today_month:
            todays_people.append(p)

    # Regra do 29/02 -> notificar em 28/02 quando não for bissexto
    if today_month == 2 and today_day == 28 and not is_leap_year(today.year):
        for p in active_birthdays:
            if p.get("day") == 29 and p.get("month") == 2:
                todays_people.append(p)

    print(f"[INFO] Birthdays today: {len(todays_people)}")

    sent_count = 0
    skipped_count = 0
    failed_count = 0

    # Para cada aniversariante do dia, aplica idempotência e enviar
    for person in todays_people:
        aniversariante_id = person.get("id")

        # chave idempotente
        key = f"{aniversariante_id}|{today_str}"
        if key in sent_keys:
            skipped_count += 1
            continue

        text = build_message(person)

        # Tenta enviar e registrar log
        created_at = datetime.now(ZoneInfo(FORTALEZA_TZ)).isoformat(timespec="seconds")

        try:
            telegram_send_message(bot_token, chat_id, text)

            log.append({
                "aniversariante_id": aniversariante_id,
                "notified_date": today_str,
                "status": "SENT",
                "error_message": None,
                "created_at": created_at
            })

            sent_keys.add(key)
            sent_count += 1

        except Exception as e:
            log.append({
                "aniversariante_id": aniversariante_id,
                "notified_date": today_str,
                "status": "FAILED",
                "error_message": str(e),
                "created_at": created_at
            })

            sent_keys.add(key)
            failed_count += 1

    # Salva log no disco
    save_json(DATA_LOG, log)

    # Resumo final (vai aparecer nos logs do Actions)
    print(f"[INFO] Sent: {sent_count} | Skipped: {skipped_count} | Failed: {failed_count}")
    print(f"[INFO] Log updated: {DATA_LOG}")


if __name__ == "__main__":
    main()