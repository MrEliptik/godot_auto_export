import os
import subprocess
import zipfile
import shutil

godot_path = 'godot.exe'
butler_path = 'butler.exe'
butler_game = 'your_username/game_name'
# Found under the Steam sdk > tools > ContentBuilder > builder
steamcmd_path = 'steamcmd.exe'
# Content folder you created under sdk > tools > ContentBuilder
steam_content_path_win = ''
steam_content_path_linux = ''
# Steam app vdf file
steam_app_script = ''
steam_credentials_path = 'steam_credentials.txt'

build_path = 'build/'
game_name = 'colorspace'
exe_name_windows = game_name+'.exe'
exe_name_linux = game_name+'.x86_64'

project_file = 'project.godot'

# Add all the templates you want here
windows_template_steam = "Windows STEAM"
windows_template_itch = "Windows ITCH"
linux_template_steam = "Linux STEAM"
linux_template_itch = "Linux ITCH"

templates = [windows_template_steam, windows_template_itch, linux_template_steam, linux_template_itch]

def parse_build_nb_from_file(file):
    # If you have a better way of parsing the file, tell me!
    with open(file, 'r', encoding='UTF-8') as f:
        for line in f:
            if 'config/version' in line:
                number = line.strip().split("config/version=", 1)[1]
                number = number.replace('"', '')
                return number

def export_template(template, build_path, build_number):
    # My template are named "Platform STORE"
    platform = template.split(' ')[0]
    store = template.split(' ')[1]
    exe_name = ""
    match platform:
        case "Windows":
            exe_name = exe_name_windows
        case "Linux":
            exe_name = exe_name_linux

    build_path_template = os.path.join(build_path, template.replace(' ', '_'))
    if not os.path.isdir(build_path_template):
        os.makedirs(build_path_template)
        print("    |---> Template folder created: " + build_path_template)
    else:
        print("    |---> Template folder already exists: " + build_path_template)

    cmd = [godot_path, "--export", template, os.path.join(build_path_template, exe_name)]
    print("    |---> Executing command: ", cmd)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
        pass
    print("    |---> Exporting template finished: ", template)

    # List files to zip
    files_to_zip = []
    for file in os.listdir(build_path_template):
        # I'm removing .so and .dll files for Itch build as I don't need the steam lib
        if store == "ITCH" and platform == "Linux":
            if file.endswith((".so")): continue
        if store == "ITCH" and platform == "Windows":
            if file.endswith((".dll")): continue
        files_to_zip.append(file)
    
    zip_file = os.path.join(build_path, game_name+'_'+platform+'_'+store+'_'+build_number+'.zip')
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as myzip:
        for file in files_to_zip:
            # File to zip, filename in zip, compression type
            myzip.write(os.path.join(build_path_template, file), file)
    
    print("    |---> Zip created: ", zip_file)
    return zip_file

def upload_itch(zip_files, build_number):
    for zip in zip_files:
        print("|---> Uploading: " + zip)
        channel = 'Windows'
        # Check what channel it is
        if 'Linux' in zip:
            channel = 'linux'
        if 'Windows' in zip:
            channel = 'windows'

        cmd = [butler_path, 'push', zip, butler_game+':'+channel, '--userversion', build_number]
        print("    |---> Executing command: ", cmd)

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
            for line in sp.stdout:
                print(line.strip())

def upload_steam(zip_files, steam_credentials):
    for zip in zip_files:
        print("|---> Uploading: " + zip)

        # Check what channel it is
        # Move zip to content folder
        if 'Linux' in zip:
            shutil.copy(zip, steam_content_path_linux)
        if 'Windows' in zip:
            shutil.copy(zip, steam_content_path_win)

    # Execute steam cmd
    cmd = [steamcmd_path, '+login', steam_credentials[0], steam_credentials[1], '+run_app_build_http', steam_app_script, '+quit']
    print("    |---> Executing command: ", cmd)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
        for line in sp.stdout:
            print(line.strip())

    # Delete zips after upload
    for file in os.listdir(steam_content_path_win):
        if file.endswith((".zip")):
            print("|---> Deleting: " + file)
            os.remove(os.path.join(steam_content_path_win, file))
    
    for file in os.listdir(steam_content_path_linux):
        if file.endswith((".zip")):
            print("|---> Deleting: " + file)
            os.remove(os.path.join(steam_content_path_linux, file))

def read_steam_credentials():
    credentials = []
    with open(steam_credentials_path, 'r', encoding='UTF-8') as f:
        for line in f:
            credentials.append(line.strip())
    return credentials

def main():
    print("########## Export starting ##########")

    build_number = parse_build_nb_from_file(project_file)

    build_path_full = os.path.join(build_path, build_number)
    print("|---> Creating export build folder: " + build_path_full)

    if not os.path.isdir(build_path_full):
        os.makedirs(build_path_full)
        print("    |---> Export folder created: " + build_path_full)
    else:
        print("    |---> Export folder already exists: " + build_path_full)

    zip_files = []
    for template in templates:
        print("|---> Exporting template: " + template)
        zip_created = export_template(template, build_path_full, build_number)
        zip_files.append(zip_created)

    print("Upload to itch? y/n")
    while(True):
        x = input()
        if x=='y':
            break
        elif x=='n':
            exit(0)

    print("########## Upload starting ##########")
    zip_files_itch = []
    for file in zip_files:
        if "ITCH" in file:
            zip_files_itch.append(file)
    upload_itch(zip_files_itch, build_number)

    print("Upload to steam? y/n")
    while(True):
        x = input()
        if x=='y':
            break
        elif x=='n':
            exit(0)
    
    print("########## Upload starting ##########")
    zip_files_steam = []
    for file in zip_files:
        if "STEAM" in file:
            zip_files_steam.append(file)
    steam_credentials = read_steam_credentials()
    upload_steam(zip_files_steam, build_number, steam_credentials)

if __name__ == '__main__':
    main()