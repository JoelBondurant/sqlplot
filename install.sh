echo "SqlPlot installing."
sudo groupadd -g 7979 sqlplot
sudo useradd -m -u 7979 -g 7979 sqlplot
PY_SITE=$(python3 -c "import site; print(site.getsitepackages()[0])")
sudo mkdir -p ${PY_SITE}
sudo su -c "pwd > ${PY_SITE}/sqlplot.pth"
echo Python3 Site: ${PY_SITE}

sudo cp query_engine.service /etc/systemd/system/
sudo cp web_engine.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl start query_engine
sudo systemctl start web_engine
sudo systemctl enable query_engine
sudo systemctl enable web_engine
echo "SqlPlot installed."
