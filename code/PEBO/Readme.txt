###User_check

sudo apt install python3-boto3

#AWS
sudo apt install awscli -y
aws --version
aws configure


###Display

sudo apt install python3-pip python3-dev python3-setuptools

sudo apt install -y i2c-tools
sudo raspi-config
#Navigate to: Interfacing Options → I2C → Enable
#Reboot afterward:

sudo reboot
i2cdetect -y 1

#Image handling (drawing text/graphics)
sudo apt install python3-pillow

#SSD1306 OLED driver
pip3 install adafruit-circuitpython-ssd1306


###Assistant
sudo apt update
sudo apt install -y python3-pip python3-numpy python3-scipy python3-sounddevice

sudo apt install python3-pygame
sudo apt install python3-pyaudio

pip3 install --break-system-packages google-generativeai
pip3 install --break-system-packages edge-tts
pip3 install --break-system-packages speechrecognition

pip3 install --break-system-packages openai-whisper
pip3 install --break-system-packages sounddevice


sudo apt install ffmpeg

##new_assistant 
pip3 install scipy --break-system-packages
pip3 install aiohttp --break-system-packages
pip3 install assemblyai --break-system-packages

###record audio
pip install noisereduce --break-system-packages




