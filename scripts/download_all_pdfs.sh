#!/usr/bin/env bash
# Download all 33 historical CHS Patient Profile PDFs.
# Usage: bash scripts/download_all_pdfs.sh

set -euo pipefail

DOWNLOAD_DIR="C:/Users/Hermes/projects/chs-data-pipeline/data/raw/patient_profiles"
mkdir -p "$DOWNLOAD_DIR"

# Array of (URL, output_filename) pairs
URLS=(
  # 2026
  "https://hhinternet.blob.core.windows.net/uploads/2026/06/correctional-health-services-patient-profile-metrics-may-2026.pdf|2026-05.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2026/05/correctional-health-services-patient-profile-metrics-april-2026.pdf|2026-04.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2026/04/correctional-health-services-patient-profile-metrics-march-2026.pdf|2026-03.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2026/03/correctional-health-services-patient-profile-metrics-february-2026.pdf|2026-02.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2026/02/correctional-health-services-patient-profile-metrics-january-2026.pdf|2026-01.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2026/01/correctional-health-services-patient-profile-metrics-december-2025.pdf|2025-12.pdf"
  # 2025
  "https://hhinternet.blob.core.windows.net/uploads/2025/12/correctional-health-services-patient-profile-metrics-november-2025.pdf|2025-11.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/11/correctional-health-services-patient-profile-metrics-october-2025.pdf|2025-10.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/10/correctional-health-services-patient-profile-metrics-september-2025.pdf|2025-09.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/09/correctional-health-services-patient-profile-metrics-august-2025.pdf|2025-08.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/08/correctional-health-services-patient-profile-metrics-july-2025.pdf|2025-07.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/07/correctional-health-services-patient-profile-metrics-june-2025.pdf|2025-06.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/06/correctional-health-services-patient-profile-metrics-may-2025.pdf|2025-05.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/05/correctional-health-services-patient-profile-metrics-april-2025.pdf|2025-04.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/04/correctional-health-services-patient-profile-metrics-march-2025.pdf|2025-03.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/04/correctional-health-services-patient-profile-metrics-february-2025.pdf|2025-02.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/03/correctional-health-services-patient-profile-metrics-january-2025.pdf|2025-01.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/01/correctional-health-services-patient-profile-metrics-december-2024.pdf|2024-12.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2025/01/correctional-health-services-patient-profile-metrics-november-2024.pdf|2024-11.pdf"
  # 2024
  "https://hhinternet.blob.core.windows.net/uploads/2024/11/correctional-health-services-patient-profile-metrics-october-2024.pdf|2024-10.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/10/correctional-health-services-patient-profile-metrics-september-2024.pdf|2024-09.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/09/correctional-health-services-patient-profile-metrics-august-2024.pdf|2024-08.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/08/correctional-health-services-patient-profile-metrics-july-2024.pdf|2024-07.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/07/correctional-health-services-patient-profile-metrics-june-2024.pdf|2024-06.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/07/correctional-health-services-patient-profile-metrics-may-2024.pdf|2024-05.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/07/correctional-health-services-patient-profile-metrics-april-2024.pdf|2024-04.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/07/correctional-health-services-patient-profile-metrics-march-2024.pdf|2024-03.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/07/correctional-health-services-patient-profile-metrics-february-2024.pdf|2024-02.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/07/correctional-health-services-patient-profile-metrics-january-2024.pdf|2024-01.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2024/04/correctional-health-services-patient-profile-metrics-december-2023.pdf|2023-12.pdf"
  # 2023
  "https://hhinternet.blob.core.windows.net/uploads/2023/12/correctional-health-services-patient-profile-metrics-november-2023.pdf|2023-11.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2023/11/correctional-health-services-patient-profile-metrics-october-2023.pdf|2023-10.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2023/11/correctional-health-services-patient-profile-metrics-september-2023.pdf|2023-09.pdf"
  "https://hhinternet.blob.core.windows.net/uploads/2023/11/correctional-health-services-patient-profile-metrics-august-2023.pdf|2023-08.pdf"
)

TOTAL=${#URLS[@]}
COUNT=0
FAILED=0

echo "Downloading $TOTAL PDFs to $DOWNLOAD_DIR"
echo ""

for entry in "${URLS[@]}"; do
  URL="${entry%%|*}"
  FNAME="${entry##*|}"
  OUTFILE="$DOWNLOAD_DIR/$FNAME"
  COUNT=$((COUNT + 1))

  if [ -f "$OUTFILE" ] && [ -s "$OUTFILE" ]; then
    echo "[$COUNT/$TOTAL] Already exists: $FNAME (skipping)"
    continue
  fi

  echo "[$COUNT/$TOTAL] Downloading $FNAME ..."
  if curl -sL -o "$OUTFILE" --connect-timeout 30 --max-time 120 "$URL"; then
    FILESIZE=$(stat -c%s "$OUTFILE" 2>/dev/null || echo "?")
    echo "       Done (${FILESIZE} bytes)"
  else
    echo "       FAILED"
    FAILED=$((FAILED + 1))
  fi
  sleep 1
done

echo ""
echo "========================"
echo "Download complete."
echo "  Total:  $TOTAL"
echo "  Failed: $FAILED"
ls -la "$DOWNLOAD_DIR" | grep -v '^total' | grep -v '\.$'
