import os
import subprocess
import zipfile
import shutil
import configparser
from argparse import ArgumentParser
from packaging.version import Version

godot_path = 'godot.exe'
gh_cli_path = 'C:\Program Files\GitHub CLI\gh.exe'
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
game_name = 'game_name'
exe_name_windows = game_name+'.exe'
exe_name_linux = game_name+'.x86_64'

project_file = 'project.godot'
export_preset_file = "export_presets.cfg"

# Add all the templates you want here
windows_template_steam = "Windows STEAM"
windows_template_itch = "Windows ITCH"
linux_template_steam = "Linux STEAM"
linux_template_itch = "Linux ITCH"

templates = [windows_template_steam, windows_template_itch, linux_template_steam, linux_template_itch]

args = {}

def print_console(to_print, override=False):
    if args.verbose or override:
        print(to_print)

def parse_latest_from_folder(path):
    subfolders = [ {"name": f.name, "path": f.path} for f in os.scandir(path) if f.is_dir() ]

    latest_build_path = ""
    latest_build = "0.0.0"

    for folder in subfolders:
        # Assume folder names are build numbers that we are going to compare
        # Assume the build number is following x.x.x
        if Version(folder["name"]) > Version(latest_build):
            latest_build = folder["name"]
            latest_build_path = folder['path']

    print_console(f"Latest build: {latest_build}, {latest_build_path}")

    return {"latest_build": latest_build, "path": latest_build_path}

def parse_build_nb_from_file(file):
    # If you have a better way of parsing the file, tell me!
    with open(file, 'r', encoding='UTF-8') as f:
        for line in f:
            if 'config/version' in line:
                number = line.strip().split("config/version=", 1)[1]
                number = number.replace('"', '')
                return number

def update_export_preset(file, build_number):
    # Remove _draft is present and add quotes in the string
    version = f'"{build_number.split("_draft", 1)[0]}"'

    print("|---> Updating export preset: " + file)
    config = configparser.ConfigParser()
    config.read(file)

    print("    |---> Version was: " + config.get('preset.0.options', 'version/name'))
    print("    |---> New version: " + version)
    config.set('preset.0.options', 'version/name', version)

    version_code = config.get('preset.0.options', 'version/code')
    print("    |---> Version was: " + version_code)
    version_code = str(int(version_code) + 1)
    print("    |---> New version: " + version_code)
    config.set('preset.0.options', 'version/code', version_code)

    with open(file, 'w') as configfile:
        config.write(configfile)

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
        print_console("    |---> Template folder created: " + build_path_template)
    else:
        print_console("    |---> Template folder already exists: " + build_path_template)

    cmd = [godot_path, "--export", template, os.path.join(build_path_template, exe_name)]
    print_console("    |---> Executing command: ", cmd)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
        pass
    print_console("    |---> Exporting template finished: ", template)

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
    
    print_console("    |---> Zip created: ", zip_file)
    return zip_file

def upload_gh(file, build_nb, prerelease=False):
    print("    |---> Uploading build: {}, prerelease: {}".format(build_nb, prerelease))
    if prerelease:
        cmd = [gh_cli_path, 'release', 'create', build_nb, file, '--generate-notes', '--prerelease']
    else:
        cmd = [gh_cli_path, 'release', 'create', build_nb, file, '--generate-notes']
    
    print("    |---> Executing command: ", cmd)
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
        for line in sp.stdout:
            print(line.strip())

def upload_itch(zip_files, build_number):
    for zip in zip_files:
        print_console("|---> Uploading: " + zip)
        channel = 'Windows'
        # Check what channel it is
        if 'Linux' in zip:
            channel = 'linux'
        if 'Windows' in zip:
            channel = 'windows'

        cmd = [butler_path, 'push', zip, butler_game+':'+channel, '--userversion', build_number]
        print_console("    |---> Executing command: ", cmd)

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
            for line in sp.stdout:
                print_console(line.strip())

def upload_steam(zip_files, steam_credentials):
    for zip in zip_files:
        print_console("|---> Uploading: " + zip)

        # Check what channel it is
        # Move zip to content folder
        if 'Linux' in zip:
            shutil.copy(zip, steam_content_path_linux)
            # Extract zip as we can't upload a zip to steam
            # We can make that better by copying the files instead of the zip.. this is a quick fix
            with zipfile.ZipFile(zip,"r") as zip_ref:
                zip_ref.extractall(steam_content_path_linux)
            #Go through files to delete the zip
            for file in os.listdir(steam_content_path_linux):
                if file.endswith((".zip")):
                    print_console("|---> Deleting: " + file)
                    os.remove(os.path.join(steam_content_path_linux, file))
        if 'Windows' in zip:
            shutil.copy(zip, steam_content_path_win)
            with zipfile.ZipFile(zip,"r") as zip_ref:
                zip_ref.extractall(steam_content_path_win)
            for file in os.listdir(steam_content_path_win):
                if file.endswith((".zip")):
                    print_console("|---> Deleting: " + file)
                    os.remove(os.path.join(steam_content_path_win, file))

    # Execute steam cmd
    cmd = [steamcmd_path, '+login', steam_credentials[0], steam_credentials[1], '+run_app_build_http', steam_app_script, '+quit']
    print_console("    |---> Executing command: ", cmd)

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, encoding='utf-8') as sp:
        for line in sp.stdout:
            print_console(line.strip())

    # Delete zips after upload
    for file in os.listdir(steam_content_path_win):
        print_console("|---> Deleting: " + file)
        os.remove(os.path.join(steam_content_path_win, file))
    
    for file in os.listdir(steam_content_path_linux):
        print_console("|---> Deleting: " + file)
        os.remove(os.path.join(steam_content_path_linux, file))

def read_steam_credentials():
    credentials = []
    with open(steam_credentials_path, 'r', encoding='UTF-8') as f:
        for line in f:
            credentials.append(line.strip())
    return credentials

def get_zip_files_for_platform(path, platform='all'):
    zip_files = []
    files = [ {'file': f.name, 'path': f.path} for f in os.scandir(path) if f.is_file() ]

    for f in files:
        if f['file'].endswith('.zip') and (platform == "all" or platform in f['file'].lower()):
            zip_files.append(f['path'])

    return zip_files

def handle_uploads(build_path, platforms=None):
    if platforms:
        platforms = platforms.split(',')
        for p in platforms:
            print(p)
            match p:
                case 'steam':
                    zip_files = get_zip_files_for_platform(build_path, p)
                    print("Zip files steam: ", zip_files)
                    # upload_steam(zip_files)
                case 'itch':
                    zip_files = get_zip_files_for_platform(build_path, p)
                    print("Zip files itch: ", zip_files)
                    # upload_itch(zip_files)
    else:
        zip_files = get_zip_files_for_platform(build_path, 'steam')
        print("Zip files steam: ", zip_files)
        # upload_steam(zip_files)
        zip_files = get_zip_files_for_platform(build_path, 'itch')
        print("Zip files itch: ", zip_files)
        # upload_itch(zip_files)

def main():
    global args

    # TODO: Parse the templates to look for OS and platforms and add them to choices
  
    parser = ArgumentParser()
    parser.add_argument("-b", "--build-type", dest="build_type",
                        help="type of build (full, demo, beta)")
    parser.add_argument("-o", "--os", dest="os",
                        help="target OS to build (windows, linux), defaults to all")
    parser.add_argument("-p", "--platform", dest="platform",
                        help="platform to build (steam, itch), defaults to all")
    parser.add_argument("-ug", "--upload-github",
                        action="store_true", dest="upload_github", default=False,
                        help="upload the build to github")
    parser.add_argument("-fu", "--force-upload",
                        action="store_true", dest="force_upload", default=False,
                        help="upload once the builds are done without asking for confirmation")
    parser.add_argument("-ul", "--upload-latest",
                        action="store_true", dest="upload_latest", default=False,
                        help="upload the latest build type specified, defaults to full build")
    parser.add_argument("-q", "--quiet",
                        action="store_true", dest="verbose", default=False,
                        help="don't print status messages to stdout")

    args = parser.parse_args()

    build_number = parse_build_nb_from_file(project_file)
    build_path_full = os.path.join(build_path, build_number)

    if args.upload_latest:
        latest_build_dict = parse_latest_from_folder(os.path.join(build_path, 'full'))

        # Go through the build folder and look for .zip files
        # Then grab the right ones for the right platform
        
        handle_uploads(latest_build_dict["path"], args.platform)
        return

    #TODO: update build version in export.cfg

    print_console("########## Export starting ##########")
    print_console("|---> Creating export build folder: " + build_path_full)
    if not os.path.isdir(build_path_full):
        os.makedirs(build_path_full)
        print_console("    |---> Export folder created: " + build_path_full)
    else:
        print_console("    |---> Export folder already exists: " + build_path_full)

    zip_files = []
    
    for template in templates:
        if args.os and not args.os in template.lower(): continue
        if args.platform and not args.platform in template.lower(): continue

        print_console("|---> Exporting template: " + template)
        zip_created = export_template(template, build_path_full, build_number)
        zip_files.append(zip_created)

    # args["build_type"]

    if args.upload_github:
        upload_gh(zip_files, build_number, prerelease='draft' in build_number)

    if args.force_upload:
        handle_uploads(build_path_full, args.platform)
    else:
        platforms = platforms.split(',')
        for p in platforms:
            match p:
                case 'itch':
                    x = input("Upload to Itch? y/n: ")
                    if x != 'y': continue
                    zip_files_itch = []
                    for file in zip_files:
                        if "ITCH" in file:
                            zip_files_itch.append(file)
                    print_console("########## Upload starting ##########")
                    upload_itch(zip_files_itch, build_number)
                case 'steam':
                    x = input("Upload to Steam? y/n: ")
                    if x != 'y': continue
                    zip_files_steam = []
                    for file in zip_files:
                        if "STEAM" in file:
                            zip_files_steam.append(file)
                    steam_credentials = read_steam_credentials()
                    print_console("########## Upload starting ##########")
                    upload_steam(zip_files_steam, build_number, steam_credentials)

if __name__ == '__main__':
    main()