import scratchattach as sa
import time
import json
import os
import threading

username = "example_username" # your username
password = "example_password" # your password
project_id = 0000000000 # your project

block_updates_file = "world.json"

session = None
cloud = None
events = None

encode_map = {
    "a": "10",
    "b": "11",
    "c": "12",
    "d": "13",
    "e": "14",
    "f": "15",
    "g": "16",
    "h": "17",
    "i": "18",
    "j": "19",
    "k": "20",
    "l": "21",
    "m": "22",
    "n": "23",
    "o": "24",
    "p": "25",
    "q": "26",
    "r": "27",
    "s": "28",
    "t": "29",
    "u": "30",
    "v": "31",
    "w": "32",
    "x": "33",
    "y": "34",
    "z": "35",
    "0": "36",
    "1": "37",
    "2": "38",
    "3": "39",
    "4": "40",
    "5": "41",
    "6": "42",
    "7": "43",
    "8": "44",
    "9": "45",
    "+": "46",
    "-": "47",
    ".": "48",
    " ": "49",
    "_": "50",
    "#": "51",
    " ": "00",
}

decode_map = {v: k for k, v in encode_map.items()}


def encode(text):
    text = text.lower()
    encoded = []
    for char in text:
        if char in encode_map:
            encoded.append(encode_map[char])
    return "".join(encoded)


def decode(encoded_text):
    decoded = []
    i = 0
    while i < len(encoded_text):
        code = encoded_text[i : i + 2]
        if code in decode_map:
            decoded.append(decode_map[code])
        i += 2
    return "".join(decoded)


def get_variables(text, encoded=False):
    if encoded:
        text = decode(text)
    variables = [var for var in text.split(" ") if var]
    return variables


def load_block_updates():
    if os.path.exists(block_updates_file):
        try:
            with open(block_updates_file, "r") as f:
                data = json.load(f)
                for key, entry in data.items():
                    if "timestamp" not in entry:
                        entry["timestamp"] = 0
                return data
        except:
            return {}
    return {}


def save_block_updates(updates):
    try:
        with open(block_updates_file, "w") as f:
            json.dump(updates, f, indent=2)
    except:
        pass


def block_update(variables, use_backup=False):
    if use_backup:
        offset = 15
    else:
        offset = 8

    blockupdateid = variables[offset]
    ic = variables[offset + 1]
    tilec = variables[offset + 2]
    heldc = variables[offset + 3]
    xcursorposition = variables[offset + 4]
    ycursorposition = variables[offset + 5]
    mousedown = variables[offset + 6]

    if mousedown != "1" and mousedown != "2":
        return False

    update_entry = {
        "blockUpdateID": blockupdateid,
        "iC": ic,
        "tileC": tilec,
        "heldC": heldc,
        "xCursorPosition": xcursorposition,
        "yCursorPosition": ycursorposition,
        "mouseDown": mousedown,
        "timestamp": time.time(),
    }

    block_updates = load_block_updates()

    if str(blockupdateid) in block_updates:
        existing = block_updates[str(blockupdateid)]
        if (
            existing.get("iC") == ic
            and existing.get("tileC") == tilec
            and existing.get("heldC") == heldc
        ):
            return False

    keys_to_remove = []
    for key, entry in block_updates.items():
        if entry.get("iC") == ic and key != str(blockupdateid):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del block_updates[key]

    block_updates[str(blockupdateid)] = update_entry
    save_block_updates(block_updates)
    return True


def server():
    global cloud

    server0_chunk_index = 0
    server1_chunk_index = 0
    last_update_count = 0

    while True:
        try:
            block_updates = load_block_updates()

            if not block_updates:
                cloud.set_var("SERVER0", "0")
                time.sleep(0.1)
                cloud.set_var("SERVER1", "0")
                time.sleep(0.1)
                cloud.set_var("SERVER2", "0")
                time.sleep(0.1)
                continue

            items = []
            for block_id, data in block_updates.items():
                item_str = f"{data['blockUpdateID']} {data['iC']} {data['tileC']} {data['heldC']} {data['xCursorPosition']} {data['yCursorPosition']} {data['mouseDown']}"
                items.append(item_str)

            chunks = []
            current_chunk = ""

            for item in items:
                test_chunk = current_chunk + (" " if current_chunk else "") + item
                encoded_test = encode(test_chunk)

                if len(encoded_test) > 256:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = item
                else:
                    current_chunk = test_chunk

            if current_chunk:
                chunks.append(current_chunk)

            if chunks:
                total_chunks = len(chunks)

                server0_chunks = [chunks[i] for i in range(0, total_chunks, 2)]
                server1_chunks = [chunks[i] for i in range(1, total_chunks, 2)]

                if server0_chunks:
                    chunk_to_send = server0_chunks[
                        server0_chunk_index % len(server0_chunks)
                    ]
                    encoded_chunk = encode(chunk_to_send)
                    cloud.set_var("SERVER0", encoded_chunk)
                    server0_chunk_index += 1
                else:
                    cloud.set_var("SERVER0", "0")

                time.sleep(0.1)

                if server1_chunks:
                    chunk_to_send = server1_chunks[
                        server1_chunk_index % len(server1_chunks)
                    ]
                    encoded_chunk = encode(chunk_to_send)
                    cloud.set_var("SERVER1", encoded_chunk)
                    server1_chunk_index += 1
                else:
                    cloud.set_var("SERVER1", "0")
            else:
                cloud.set_var("SERVER0", "0")
                time.sleep(0.1)
                cloud.set_var("SERVER1", "0")

            time.sleep(0.1)

            sorted_updates = sorted(
                block_updates.items(),
                key=lambda x: x[1].get("timestamp", 0),
                reverse=True,
            )

            server2_chunk = ""
            items_included = 0

            for block_id, data in sorted_updates:
                item_str = f"{data['blockUpdateID']} {data['iC']} {data['tileC']} {data['heldC']} {data['xCursorPosition']} {data['yCursorPosition']} {data['mouseDown']}"
                test_chunk = server2_chunk + (" " if server2_chunk else "") + item_str
                encoded_test = encode(test_chunk)

                if len(encoded_test) > 256:
                    break
                else:
                    server2_chunk = test_chunk
                    items_included += 1

            if server2_chunk:
                encoded_chunk = encode(server2_chunk)
                cloud.set_var("SERVER2", encoded_chunk)

            time.sleep(0.1)

        except:
            time.sleep(0.1)


print("logging in...")
session = sa.login(username, password)

if session:
    print("logged in")
    cloud = session.connect_cloud(project_id)
    events = cloud.events()

    @events.event
    def on_set(activity):
        try:
            value = activity.value
            variables = get_variables(value, encoded=True)

            xposition = variables[0]
            yposition = variables[1]
            headdirection = variables[2]
            armdirection = variables[3]
            iswalking = variables[4]
            i_s = variables[5]
            username = variables[6]
            pingtimer = variables[7]

            blockupdateid = variables[8]
            ic = variables[9]
            tilec = variables[10]
            heldc = variables[11]
            xcursorposition = variables[12]
            ycursorposition = variables[13]
            mousedown = variables[14]

            backup_blockupdateid = variables[15] if len(variables) > 15 else "0"
            backup_ic = variables[16] if len(variables) > 16 else "0"
            backup_tilec = variables[17] if len(variables) > 17 else "0"
            backup_heldc = variables[18] if len(variables) > 18 else "0"
            backup_xcursorposition = variables[19] if len(variables) > 19 else "0"
            backup_ycursorposition = variables[20] if len(variables) > 20 else "0"
            backup_mousedown = variables[21] if len(variables) > 21 else "0"

            primary_processed = False

            if mousedown == "1" or mousedown == "2":
                primary_processed = block_update(variables, use_backup=False)

            if len(variables) > 20 and (
                backup_mousedown == "1" or backup_mousedown == "2"
            ):
                backup_is_different = (
                    backup_blockupdateid != blockupdateid
                    or backup_ic != ic
                    or backup_tilec != tilec
                    or backup_heldc != heldc
                    or backup_xcursorposition != xcursorposition
                    or backup_ycursorposition != ycursorposition
                )

                if backup_is_different:
                    if backup_ic != ic:
                        block_update(variables, use_backup=True)
                    elif backup_blockupdateid != blockupdateid:
                        block_update(variables, use_backup=True)
                    else:
                        if backup_tilec != tilec or backup_heldc != heldc:
                            block_update(variables, use_backup=True)
        except:
            pass

    @events.event
    def on_ready():
        print("connected")
        server_thread = threading.Thread(target=server)
        server_thread.daemon = True
        server_thread.start()

    events.start(thread=False)
    print("listening...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopping")
        events.stop()
else:
    print("login failed")
