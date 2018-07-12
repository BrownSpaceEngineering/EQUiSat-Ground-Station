# installs the EQUiSat groundstation on a RPi system

# dependencies
sudo apt-get install -y python-serial
pip install -r requirements.txt

# reedsolomon
make -C ./groundstation/reedsolomon

# systemctl startup service
sudo cp ./equistation.service /etc/systemd/system/

echo "enable the system service with:"
echo "'sudo systemctl enable equistation.service'"
echo "control the system service with:"
echo "'sudo systemctl start|stop|status equistation.service'"
