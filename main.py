
#Luis Miguel Cañaveral y Maria Jose Arcila

from bot import Bot, Conversation, ReplyKeyboardMarkup, KeyboardButton
import utime
import network, urequests
from machine import RTC, I2C, Pin, PWM
from ssd1306 import SSD1306_I2C
import privado
import _thread

hora_recordatorio = ""
chat_id = ""
bandera = False
bocina = None

def activar_bocina():
    global bocina
    bocina_pin = Pin(25, Pin.OUT)
    bocina = PWM(bocina_pin)
    bocina.freq(412)
    bocina.duty(512)
    utime.sleep(5)
    bocina.duty(0)

# Función para el reloj
def reloj():
    global hora_recordatorio, chat_id, bot, bandera

    # datos wifi
    ssid = "Wokwi-GUEST"
    password = ""
    # API hora
    url = "http://worldtimeapi.org/api/timezone/America/Bogota"  # zonas en: http://worldtimeapi.org/timezones

    print("Conectando ...")

    # conexion OLED
    try:
        i2c = I2C(0, scl=Pin(22), sda=Pin(21))
        oled = SSD1306_I2C(128, 64, i2c)
        oled.fill(0)
        oled.text("Conectando ...", 0, 0)
        oled.show()
    except Exception as e:
        print("Error inicializando OLED:", e)

    rtc = RTC()

    # conexion wifi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(ssid, password)

    while not wifi.isconnected():
        pass

    print("IP:", wifi.ifconfig()[0], "\n")
    oled.text("Conectado con IP: ", 0, 35)
    oled.text(" " + str(wifi.ifconfig()[0]), 0, 45)
    oled.show()

    # peticiones a la API
    ultima_peticion = 0
    intervalo_peticiones = 60  # en segundos

    while True:
        if not wifi.isconnected():
            print("Fallo de conexión a WiFi")
            machine.reset()

        if (utime.time() - ultima_peticion) >= intervalo_peticiones:
            try:
                response = urequests.get(url)

                if response.status_code == 200:
                    # obtencion hora
                    datos_objeto = response.json()
                    fecha_hora = str(datos_objeto["datetime"])
                    año = int(fecha_hora[0:4])
                    mes = int(fecha_hora[5:7])
                    día = int(fecha_hora[8:10])
                    hora = int(fecha_hora[11:13])
                    minutos = int(fecha_hora[14:16])
                    segundos = int(fecha_hora[17:19])
                    sub_segundos = int(round(int(fecha_hora[20:26]) / 10000))
                
                    rtc.datetime((año, mes, día, 0, hora, minutos, segundos, sub_segundos))
                    ultima_peticion = utime.time()
                else:
                    print("Respuesta no válida: RTC no actualizado")
            except Exception as e:
                print("Error al obtener la hora:", e)

        # formateo fecha y hora
        fecha_pantalla = "Fecha:{2:02d}/{1:02d}/{0:4d}".format(*rtc.datetime())
        hora_pantalla = "Hora: {4:02d}:{5:02d}:{6:02d}".format(*rtc.datetime())
        # impresion fecha y hora en pantalla
        oled.fill(0)
        oled.text("ESP32 Reloj Web", 0, 5)
        oled.text(fecha_pantalla, 0, 25)
        #oled.text(hora_pantalla, 0, 45)
        oled.text(hora_pantalla[:-3], 0, 45)
        oled.show()

        hora_actual = "{:02d}:{:02d}".format(*rtc.datetime()[4:6])
        if hora_actual == hora_recordatorio and bandera:
            bot.send_message(chat_id, 'Alarma activa, Hora de hacer tu tarea')
            bandera = False
            _thread.start_new_thread(activar_bocina, ())
        
        utime.sleep(0.1)



# TOKEN DE TELEGRAM
TOKEN = privado.token
# BOT
bot = Bot(TOKEN)

# Definir conversación para establecer recordatorios
recordatorio = Conversation(['tiempo', 'hora'])

@recordatorio.add_command_handler('ENTRY', 'start')
def inicio(update):
    update.reply('Hola')
    update.reply('Coloca /alarma para empezar')
    return 'tiempo'

@recordatorio.add_command_handler('tiempo', 'alarma')
def establecer_recordatorio(update):
    update.reply('Ingresa la hora en formato HH:MM 24h para establecer la alarma')
    return 'hora'

@recordatorio.add_message_handler('hora', '^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
def establecer_hora(update):
    global hora_recordatorio, chat_id, bandera
    hora_recordatorio = update.message['text']
    chat_id = update.message['chat']['id']
    bandera = True
    update.reply('Alarma establecida')
    return recordatorio.END

# Agregar el manejador de conversación al bot
bot.add_conversation_handler(recordatorio)

# Iniciar el bucle del bot y la función del reloj en paralelo
bot.start_loop(reloj)


