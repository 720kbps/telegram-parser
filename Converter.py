import collections.abc
import json
#Sa nu uit si Instagram sa fac
#1.Primul ever mesaj (instagram + telegram)
#2.Numar total de mesaje - DONE
#3.Numar individual de mesaje si procentul de diferenta - DONE
#4.Numarul de mesaje vocal/video AKA lost information
#5.Top 10 zile dupa numarul de mesaje + descriere
#6.Cate mesaje per fiecare luna
#7.Numarul de memuri trimise pe insta
#8.Cele mai populare mesaje si number of occurances
#9.Statistica la anumite cuvinte (capy, pulica, etc.)
#10.Messages to emojis ration (worst days ).


file_path = 'D:\Personal Projects\ChatExport\chat.json'
conversation1 = open(file_path, 'r', encoding="utf8")
content = conversation1.read()
jsonText = json.loads(content)
fromBogdan = 0
fromNastea = 0
numberOfMessages = 0
for i in jsonText["messages"]:
    # numberOfMessages = numberOfMessages + 1
    if "media_type" in i:
        fromUser = i["from"]
        print(fromUser + ": ", end='')
        print(i["media_type"])
        continue
    if "from" in i:
        fromUser = i["from"]
        print(fromUser + ": ", end='')
        # if fromUser == "Bodgan":
        #     fromBogdan = fromBogdan + 1
        # else:
        #     fromNastea = fromNastea + 1
    else:
        print("nui in from")
    messageText = i["text"]
    if messageText == '' and "photo" in i:
        print("nui inclus in file", end='')
    elif 
        messageText = messageText[0]
    print(messageText)
print("Numarul total de mesaje:", numberOfMessages)
print("Mesaje de la Bogdan: ", fromBogdan)
print("Mesaje de la Nastea: ", fromNastea)

