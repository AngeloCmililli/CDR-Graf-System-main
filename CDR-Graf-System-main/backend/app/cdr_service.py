import os
from collections import defaultdict
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
configured_csv_path = os.getenv("CSV_FILE_PATH")
if configured_csv_path:
    CSV_PATH = Path(configured_csv_path)
    if not CSV_PATH.is_absolute():
        CSV_PATH = BASE_DIR / CSV_PATH
else:
    csv_candidates = [
        BASE_DIR / "data" / "Master.csv",
        Path(__file__).resolve().parent / "data" / "Master.csv",
    ]
    CSV_PATH = next((path for path in csv_candidates if path.exists()), csv_candidates[0])

HOURS = list(range(8, 17))
CARRIER_NAMES = {
    "movistar": "Movistar Móvil",
    "digitel": "Digitel Móvil",
    "movilnet": "Movilnet Móvil",
    "cantv": "CANTV Fijo",
}
STATUS_ALIASES = {
    "ANSWERED": "ans",
    "ANSWER": "ans",
    "NO ANSWER": "noans",
    "NOANSWER": "noans",
    "BUSY": "busy",
    "FAILED": "fail",
    "CONGESTION": "fail",
    "CHANUNAVAIL": "fail",
}

TRUNK_DISPLAY_NAMES = {

    "SIP/INCONCERT_OUT": "inConcert Saliente",
    "SIP/INCONCERT_IN": "inConcert Entrante",
    "SIP/CPA_SIP_1": "CPA SIP Troncal 1",
    "SIP/CPA_SIP_2": "CPA SIP Troncal 2",
    "SIP/ITXINTER0IMG0CCS": "Interconexión ITX Caracas",
    "SIP/ITXINTER0IMG0VAL": "Interconexión ITX Valencia",
    "SIP/PBX_H1CCS_1_OUT": "PBX Hospital 1 Caracas",
    "SIP/PBX_H1MBO_1_OUT": "PBX Hospital 1 Maracaibo",
    "SIP/PBX_H1BQT_1_OUT": "PBX Hospital 1 Barquisimeto",
    "SIP/BANESCO": "Enlace Banesco",
    "SIP/SERVIDOR_2": "Servidor SIP Auxiliar 2",
    "SIP/SERVIDOR_3": "Servidor SIP Auxiliar 3",
    "SIP/GGGG_TRUNK_OUT1": "Troncal GGGG Saliente 1",
    "SIP/TATA_PROVICIONAL": "Enlace TATA Internacional",
    "SIP/LDTELECOM_3_OUT": "LD Telecom Saliente 3",
}


def get_trunk_display_name(raw_name: str | None, direction: str = "in") -> str:
    """
    Retorna un nombre legible y descriptivo para la troncal SIP.
    Si la troncal no tiene un mapeo explícito, genera un nombre limpio retirando el prefijo 'SIP/'.
    """
    if not raw_name:
        return "Troncal Desconocida"

    normalized = raw_name.strip()

    if normalized in TRUNK_DISPLAY_NAMES:
        return TRUNK_DISPLAY_NAMES[normalized]

    clean_name = normalized

    if clean_name.startswith("SIP/"):
        clean_name = clean_name[4:]
    return clean_name.replace("_", " ").title()
        


def _empty_metrics():
    result = {}
    for key, name in [("all", "Todas las Operadoras"), *CARRIER_NAMES.items()]:
        result[key] = {
            "name": name,
            "total": 0,
            "ans": 0,
            "noans": 0,
            "busy": 0,
            "fail": 0,
            "asr": "0.0%",
            "acd": "00:00",
            "channels": "N/D / 60",
            "hourly": [0] * len(HOURS),
            "operators": [0] * len(CARRIER_NAMES),
        }
    result.update({"trunks_in": [], "trunks_out": []})
    return result


def _carrier_expression():
    return """
        CASE
                        WHEN column17 LIKE '%1210%' OR column17 LIKE '%1211%'
                            OR column17 LIKE '%4110%' OR column17 LIKE '%4111%'
                            OR column01 LIKE '0414%' OR column01 LIKE '0424%'
                            OR column01 LIKE '0214%' OR column01 LIKE '0224%' THEN 'movistar'
                        WHEN column17 LIKE '%1230%'
                            OR column01 LIKE '0416%' OR column01 LIKE '0426%'
                            OR column01 LIKE '0216%' OR column01 LIKE '0226%' THEN 'movilnet'
                        WHEN column17 LIKE '%1220%' OR column01 LIKE '0251%' THEN 'cantv'
                        WHEN column17 LIKE '%4140%' OR column17 LIKE '%4141%'
                            OR column01 LIKE '0412%' OR column01 LIKE '0422%'
                            OR column01 LIKE '0212%' OR column01 LIKE '0222%' THEN 'digitel'
            ELSE 'otros'
        END
    """


def _format_duration(seconds):
    total_seconds = max(0, int(round(seconds or 0)))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def get_dashboard_metrics():
    metrics = _empty_metrics()
    if not CSV_PATH.exists():
        metrics["error"] = f"Archivo {CSV_PATH} no encontrado."
        return metrics

    connection = duckdb.connect(database=":memory:")
    try:
        escaped_path = str(CSV_PATH).replace("'", "''")
        connection.execute(
            "CREATE VIEW cdr_data AS "
            f"SELECT * FROM read_csv_auto('{escaped_path}', header=false, all_varchar=true)"
                )
        connection.execute(                 
                    f"""
                    CREATE VIEW normalized_cdr AS
                    SELECT
                        ({_carrier_expression()}) AS carrier,
                        UPPER(TRIM(COALESCE(CAST(column14 AS VARCHAR), ''))) AS status,
                        TRY_CAST(column09 AS TIMESTAMP) AS call_time,
                        TRY_CAST(column13 AS DOUBLE) AS duration,
                        NULLIF(TRIM(split_part(CAST(column05 AS VARCHAR), '-', 1)), '') AS trunk_in,
                        NULLIF(TRIM(split_part(CAST(column06 AS VARCHAR), '-', 1)), '') AS trunk_out
                    FROM cdr_data
                    """
                )
        
        total_calls = connection.execute(
                    "SELECT COUNT(*) FROM normalized_cdr"
                ).fetchone()[0]
        
        grouped = connection.execute(
                    """
                    SELECT carrier, status, EXTRACT(HOUR FROM call_time) AS hour,
                           COUNT(*) AS total,
                           AVG(duration) FILTER (WHERE status IN ('ANSWERED', 'ANSWER')) AS acd
                    FROM normalized_cdr
                    GROUP BY carrier, status, hour
                    """
                ).fetchall()

        aggregates = defaultdict(lambda: {
            "total": 0,
            "ans": 0,
            "noans": 0,
            "busy": 0,
            "fail": 0,
            "duration_sum": 0.0,
            "duration_count": 0,
            "hourly": [0] * len(HOURS),
            "inbound": 0,
            "outbound": 0,
        })
        for carrier, status, hour, count, average_duration in grouped:
            status_key = STATUS_ALIASES.get(status)
            targets = ["all"]
            if carrier in CARRIER_NAMES:
                targets.append(carrier)
            for target in targets:
                aggregate = aggregates[target]
                aggregate["total"] += count
                if status_key:
                    aggregate[status_key] += count
                if hour is not None and int(hour) in HOURS:
                    aggregate["hourly"][int(hour) - HOURS[0]] += count
                if status_key == "ans" and average_duration is not None:
                    aggregate["duration_sum"] += average_duration * count
                    aggregate["duration_count"] += count

        direction_rows = connection.execute(
            """
            SELECT carrier, COUNT(trunk_in), COUNT(trunk_out)
            FROM normalized_cdr
            GROUP BY carrier
            """
        ).fetchall()
        for carrier, inbound, outbound in direction_rows:
            targets = ["all"]
            if carrier in CARRIER_NAMES:
                targets.append(carrier)
            for target in targets:
                aggregates[target]["inbound"] += inbound
                aggregates[target]["outbound"] += outbound

        operator_order = list(CARRIER_NAMES)
        for key in ["all", *operator_order]:
            aggregate = aggregates[key]
            target = metrics[key]
            target.update({
                "total": aggregate["total"],
                "ans": aggregate["ans"],
                "noans": aggregate["noans"],
                "busy": aggregate["busy"],
                "fail": aggregate["fail"],
                "inbound": aggregate["inbound"],
                "outbound": aggregate["outbound"],
                "asr": f"{(aggregate['ans'] / aggregate['total'] * 100) if aggregate['total'] else 0:.1f}%",
                "acd": _format_duration(
                    aggregate["duration_sum"] / aggregate["duration_count"]
                    if aggregate["duration_count"] else 0
                ),
                "hourly": aggregate["hourly"],
                "operators": [
                    aggregates[carrier]["total"] for carrier in operator_order
                ],
            })

        metrics["all"]["operators"] = [
            aggregates[carrier]["total"] for carrier in operator_order
        ]
        for key in operator_order:
            metrics[key]["operators"] = [
                metrics[key]["total"] if key == carrier else 0
                for carrier in operator_order
            ]

        for metric_key, column in [("trunks_in", "trunk_in"), ("trunks_out", "trunk_out")]:
            rows = connection.execute(
                f"""
                SELECT carrier, {column}, COUNT(*) AS total
                FROM normalized_cdr
                WHERE {column} IS NOT NULL
                GROUP BY carrier, {column}
                ORDER BY total DESC
                LIMIT 20
                """
            ).fetchall()
            direction = "in" if metric_key == "trunks_in" else "out"
            metrics[metric_key] = [
                {
                    "name": get_trunk_display_name(trunk, direction=direction),
                    "raw_name": trunk,
                    "value": count,
                    "carrier": carrier,
                }
                for carrier, trunk, count in rows
            ]

        metrics["total_calls"] = total_calls
        metrics["carrier_count"] = sum(
            1 for key in operator_order if metrics[key]["total"] > 0
        )
        return metrics
    except Exception as error:
        metrics["error"] = f"No se pudieron procesar los CDR: {error}"
        return metrics
    finally:
        connection.close()