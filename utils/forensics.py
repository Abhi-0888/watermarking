import datetime


def parse_watermark_text(watermark_text):
    parts = {}
    for item in watermark_text.split("|"):
        token = item.strip()
        if ":" in token:
            key, value = token.split(":", 1)
            key = key.strip()
            value = value.strip()
            alias_map = {
                "ISS": "Issuer",
                "RCV": "Receiver",
                "DOC": "DocID",
                "TS": "Time",
            }
            parts[alias_map.get(key, key)] = value
    return parts


def generate_forensic_report(watermark_text, file_path):
    report = {
        "file_path": file_path,
        "report_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watermark_text": watermark_text,
        "suspected_recipient": None,
        "document_id": None,
        "issued_at": None,
        "traceable": bool(watermark_text),
    }

    if watermark_text:
        parts = parse_watermark_text(watermark_text)
        report["suspected_recipient"] = parts.get("Receiver") or parts.get("User")
        report["document_id"] = parts.get("DocID")
        report["issued_at"] = parts.get("Time")

    print("\n" + "=" * 58)
    print("FORENSIC LEAK REPORT")
    print("=" * 58)
    print(f"Leaked File        : {report['file_path']}")
    print(f"Report Time        : {report['report_time']}")
    if report["traceable"]:
        print(f"Embedded Watermark : {report['watermark_text']}")
        print(f"Suspected Recipient: {report['suspected_recipient'] or 'Unknown'}")
        print(f"Document ID        : {report['document_id'] or 'Unknown'}")
        print(f"Issued At          : {report['issued_at'] or 'Unknown'}")
        print("Action             : Investigate the traced recipient copy.")
    else:
        print("Embedded Watermark : Not recovered")
        print("Action             : Leak source could not be identified")
    print("=" * 58 + "\n")

    return report
