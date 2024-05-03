# Simply following the Python markdown's versioning format since it is good enough for me.
# __version_info__ format:
#     (major, minor, patch, dev/alpha/beta/rc/final, #)
#     (1, 1, 2, 'dev', 0) => "1.1.2.dev0"
#     (1, 1, 2, 'alpha', 1) => "1.1.2a1"
#     (1, 2, 0, 'beta', 2) => "1.2b2"
#     (1, 2, 0, 'rc', 4) => "1.2rc4"
#     (1, 2, 0, 'final', 0) => "1.2.0"
import requests
import time
from Lib.prettier import Prettify
__version_info__ = (1, 2, 1, 'final', 0)

def _get_version(version_info, implicit=False):
    " Returns a PEP 440-compliant version number from version_info. "
    assert len(version_info) == 5
    assert version_info[3] in ('dev', 'alpha', 'beta', 'rc', 'final')

    if implicit:
        parts = 2 if version_info[2] == 0 else 3
    else:
        parts = 3
    v = '.'.join(map(str, version_info[:parts]))

    if version_info[3] == 'dev':
        v += '.dev' + str(version_info[4])
    elif version_info[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}
        v += mapping[version_info[3]] + str(version_info[4])
    return v

class UpdateInformation:
    Name_ver = "gogoR2"
    Version_Host = "https://raw.githubusercontent.com/Kinuseka/Kinuseka.github.io/main/external%20resource/upd_nh.json"
    Current_Version: list = __version_info__[:4]
    Version: list = None
    Message: str = None
    Additional: dict = {}
    #Additional Features
    Broadcast: str = None
    Targeted: list = None
    #Library Versioning
    A_MaV = 0
    A_MiV = 0
    A_PaV = 0
    A_Mes = None
    #Internal process checks
    initialized = False
    init_error = None

def sort_data(req: requests.Response, test = False):
    if test:
        data = ...
    else:
        data: dict = req.json()[UpdateInformation.Name_ver]
    version = data['Version']
    UpdateInformation.Message = data.get('Message', None)
    UpdateInformation.Additional = data.get('Additional', {})
    UpdateInformation.Version = data.get('Version', None)

def RemoteVersion():
    return UpdateInformation.Version

def CurrentVersion():
    return UpdateInformation.Current_Version

def ConstructVersion(Version: list):
    return f"{Version[0]}.{Version[1]}.{Version[2]}"

def Comparator(version, remote):
    v1_parts = version
    v2_parts = remote
    new_version = False
    ftr_version = False
    for num, (v1, v2) in enumerate(zip(v1_parts, v2_parts)):
        if num == 0:
            if v1 > v2:
                ftr_version = True
            elif v1 < v2:
                new_version = True
        elif num == 1:
            if new_version or ftr_version:
                break
            elif v1 > v2:
                ftr_version = True
            elif v1 < v2:
                new_version = True
        elif num == 2:
            if new_version or ftr_version:
                break
            elif v1 > v2:
                ftr_version = True
            elif v1 < v2:
                new_version = True
    return new_version, ftr_version

def Targeted_Msg(client_version, targeted):
    if targeted:
        for target in targeted:
            print(target, client_version)
            if not any(Comparator(client_version, target['for'])):
                return target['message']
    return False
def init():
    try:
        req = requests.get(UpdateInformation.Version_Host)
        sort_data(req)
        if UpdateInformation.Additional.get('New_Host', None):
            UpdateInformation.Version_Host = UpdateInformation.Additional['New_Host']
            return init()
        UpdateInformation.Broadcast = UpdateInformation.Additional.get('Broadcast', None)
        UpdateInformation.Targeted = UpdateInformation.Additional.get('Targeted', None)
        UpdateInformation.initialized = True
    except Exception as e:
        UpdateInformation.init_error = e

def show_update(prettify: Prettify):
    notification = False
    version_notice = False
    for t in range(0,5):
        if UpdateInformation.initialized:
            break
        if UpdateInformation.init_error:
            prettify.add_line(f'Error occured checking for update. Host: {UpdateInformation.Version_Host}')
            notification = True
            return notification
        time.sleep(1)
    else: 
        prettify.add_line(f'Could not fetch update details from: {UpdateInformation.Version_Host}')
        notification = True
        return notification
    new_update, future_update = Comparator(CurrentVersion()[:3], RemoteVersion())
    if new_update:
        prettify.add_line(f"A New Version is available!")
        prettify.add_line(f"Your version: v{ConstructVersion(CurrentVersion())} | Latest version: v{ConstructVersion(RemoteVersion())}")
        notification = True
        version_notice = True
    elif future_update:
        prettify.add_line("This is an unreleased version, might be unstable.")
        prettify.add_line(f"Your version: v{ConstructVersion(CurrentVersion())} | Latest version: v{ConstructVersion(RemoteVersion())}")
        notification = True
        version_notice = True
    message = UpdateInformation.Message
    broadcast = UpdateInformation.Broadcast
    targeted = Targeted_Msg(CurrentVersion(), UpdateInformation.Targeted)
    if version_notice and any((message, broadcast, targeted)):
        prettify.add_tab("Message",lines=50, char='-')
    if all((new_update, message)) or all((future_update, message)):
        saved = prettify.alignment
        prettify.define_alignment()
        prettify.add_line(f"[Log]: {message}")
        prettify.alignment = saved
        notification = True
    if targeted:
        prettify.add_line(f"[Notice]: {targeted}")
        notification = True
    if broadcast:
        prettify.add_line(f"[Broadcast]: {broadcast}")
        notification = True
    return notification

__version__ = _get_version(__version_info__, implicit=True)