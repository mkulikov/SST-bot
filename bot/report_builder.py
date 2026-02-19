from config import REGION


def build_sst_report(sst_data, station_ids):
    report_lines = []
    another_stations = []
    for station in sst_data:
        if station.get("istNo") in station_ids:
            temp = station.get("denizSicaklik")
            county = station.get("il")
            city = station.get("ilce")
            station_id = station.get("istNo")
            report_lines.append(f"{station_id} {city}/{county} {temp}°C")
        elif station.get("il") == REGION:
            another_stations.append(f"{station.get('istNo')}")
    report = "\n".join(report_lines) if report_lines else "No data available"
    if another_stations:
        report += f"\nAnother {REGION} stations: " + " ".join(another_stations)
    return report
