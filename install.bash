# installs the EQUiSat groundstation on a RPi system

# dependencies
sudo apt-get install -y python-serial

# systemctl startup service
cp ./equistation.service /usr/lib/systemd/user/
sudo systemctl enable equistation.service
sudo systemctl start equistation.service

echo "control the system service with:"
echo "'sudo systemctl start|stop|status equistation.service'"
