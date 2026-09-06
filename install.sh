#!/data/data/com.termux/files/usr/bin/bash
set -e

pkg update -y
pkg install -y git python

python -m pip install -r requirements.txt

echo
echo "KRYPT kurulumu tamamlandi."
echo "Baslatmak icin:"
echo "python krypt.py"
