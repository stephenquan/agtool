#!/usr/bin/python

import os, sys, requests, json, getpass, time, math, re

settings_path = os.path.expanduser( "~/.config/Esri/agtool/agtool.json" )
settings = { }

portalUrl = "https://www.arcgis.com"

k_default_username = "default_username"
k_password = "password"
k_token = "token"
k_expires = "expires"

def load_json_file( path ):
    if not os.path.isfile( path ):
        return { }
    with open( path, "r" ) as data_file:
        return json.loads( data_file.read() )

def save_json_file( path, obj ):
    dirname = os.path.dirname( path )
    if not os.path.exists( dirname ):
        os.makedirs( dirname )
    with open( path, "w" ) as data_file:
        json.dump( obj, data_file, indent=4, sort_keys=True )

def load_settings():
    global settings
    settings = load_json_file( settings_path )

def save_settings():
    save_json_file( settings_path, settings )

def get_settings( key, defaultValue="" ):
    return settings[ key ] if key in settings else defaultValue

def set_settings( key, value ):
    global settings
    if get_settings( key ) == value:
        return
    settings[ key ] = value
    save_settings()

def remove_settings( key ):
    global settings
    if not key in settings:
        return
    settings.pop( key )
    save_settings()

def get_default_username():
    return get_settings( k_default_username )

def set_default_username( username ):
    set_settings( k_default_username, username )

def get_user_settings( key, defaultValue="", username="" ):
    if username == "":
        username = get_default_username()
    return get_settings( username + "-" + key, defaultValue )

def set_user_settings( key, value, username="" ):
    if username == "":
        username = get_default_username()
    set_settings( username + "-" + key, value )

def remove_user_settings( key, username="" ):
    if username == "":
        username = get_default_username()
    remove_settings( username + "-" + key )

def get_token():
    token = get_user_settings( k_token )
    if token == "":
        return token
    expires = get_expires()
    if time.time() * 1000.0 >= expires:
        return ""
    return token

def get_token_ex( args ):
    username = get_default_username()
    if "username" in args[ "options" ]:
        username = args[ "options" ][ "username" ]
        set_default_username( username )
    token = get_token()
    if token == "":
        cmd_login( args )
        token = get_token()
    return token

def set_token( token ):
    set_user_settings( k_token, token )

def remove_token( ):
    remove_user_settings( k_token )

def get_expires():
    return get_user_settings( k_expires, 0 )

def set_password( password ):
    set_user_settings( k_password, password )

def remove_password( ):
    remove_user_settings( k_password )

def get_password():
    return get_user_settings( k_password )

def set_expires( expires ):
    set_user_settings( k_expires, expires )

def remove_expires( ):
    remove_user_settings( k_expires )

def passthru_option( option ):
    if option == "username":
        return False
    if option == "password":
        return False
    if option == "save":
        return False
    if option == "forget":
        return False
    return True

def unary_option( option ):
    if option == "save":
        return True
    if option == "forget":
        return True
    return False

def parse_args():
    args = { }
    args[ "parameters" ] = [ ]
    args[ "options" ] = { }
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[ i ]
        i += 1
        if arg.startswith("--"):
            key = arg[2:]
            if unary_option( key ):
                args[ "options" ][key] = "true"
            else:
                value = sys.argv[ i ]
                i += 1
                args[ "options" ][key] = value
        else:
            args[ "parameters" ].append(arg)
    if (len(args[ "parameters" ]) >= 2):
        regexp = r"^([^:]+)[:](.*)$"
        m = re.match( regexp, args[ "parameters" ][1] )
        if m is not None:
            username = m.groups()[0]
            args[ "options" ][ "username" ] = username
            args[ "parameters" ][1] = m.groups()[1]
            set_default_username( username )
    return args

def get_user_input( prompt, defaultValue="" ):
    if defaultValue != "":
        prompt = prompt + "[ " + defaultValue + " ]: "
    value = raw_input( prompt )
    return value if value != "" else defaultValue

def elapsed_str( ms ):
    sec = math.trunc( ms / 1000.0 )
    if sec < 60:
        return str(sec) + " seconds"
    min = math.trunc( sec / 60.0 )
    return str(min) + " minutes"

def get_folder_id( folder_title ):
    username = get_default_username()
    if username == "":
        cmd_login()
    token = get_token()
    if token == "":
        print "Not logged in"
        return
    url = portalUrl + "/sharing/rest/content/users/" + username
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    if "folders" not in response.json():
        print json.dumps( response.json(), indent=4, sort_keys=True )
        return ""
    for folder in response.json()[ "folders" ]:
        if folder[ "title" ] == folder_title:
            return folder[ "id" ]
    return ""

def get_item_id( item_title, folder_id=""):
    username = get_default_username()
    if username == "":
        cmd_login()
    token = get_token()
    if token == "":
        print "Not logged in"
        return
    url = portalUrl + "/sharing/rest/content/users/" + username
    if folder_id != "":
        url = url + "/" + folder_id
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    for item in response.json()[ "items" ]:
        if item[ "title" ] == item_title:
            return item[ "id" ]
    return ""

def xstr( s ):
    return s if s is not None else ""

def crack_folder( folder_path ):
    regexp = r"(?:(?:/)?(.*))$"
    m = re.match( regexp, folder_path )
    folder_title = xstr( m.groups()[0] )
    folder_id = ""
    if folder_title != "":
        folder_id = get_folder_id( folder_title )
    result = { }
    result[ "folder_title" ] = folder_title
    result[ "folder_id" ] = folder_id
    return result

def crack_item( item_path ):
    regexp = r"(?:(?:/)?(.*[^/])(?:/))?([^\/]*)$"
    m = re.match( regexp, item_path )
    folder_title = xstr( m.groups()[0] )
    folder_id = ""
    if folder_title != "":
        folder_id = get_folder_id( folder_title )
    item_title = xstr( m.groups()[1] )
    item_id = get_item_id( item_title, folder_id )
    result = { }
    result[ "folder_title" ] = folder_title
    result[ "folder_id" ] = folder_id
    result[ "item_title" ] = item_title
    result[ "item_id" ] = item_id
    result[ "item_path" ] = item_title if folder_title == "" else folder_title + "/" + item_title
    return result

def cmd_cat( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    if len( args[ "parameters" ] ) < 1:
        print "cat what?"
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print "cat: " + item_path + ": No such file or directory"
        return
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        item_path = item_obj[ "item_path" ]
        print "cat: " + item_path + ": No such file or directory"
        return
    url = portalUrl + "/sharing/rest/content/items/" + item_id + "/data"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    # print response.text
    sys.stdout.write( response.text )
    sys.stdout.flush()

def cmd_info( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    if len( args[ "parameters" ] ) < 1:
        print "info what?"
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print "info: " + item_path + ": No such file or directory"
        return
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        item_path = item_obj[ "item_path" ]
        print "info: " + item_path + ": No such file or directory"
        return
    url = portalUrl + "/sharing/rest/content/items/" + item_id
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    print json.dumps( response.json(), indent=4, sort_keys=True )

def cmd_ls( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    folder_id = ""
    if len( args[ "parameters" ] ) >= 2:
        folder_obj = crack_folder( args[ "parameters" ][1] )
        folder_id = folder_obj[ "folder_id" ]
        folder_title = folder_obj[ "folder_title" ]
        if folder_id == "":
            print "ls: " + folder_title + ": No such directory"
            return
        url = url + "/" + folder_id
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    if "folders" in response.json():
        for folder in response.json()[ "folders" ]:
            print folder[ "title" ] + "/"
    for item in response.json()[ "items" ]:
        item_name = item[ "name" ]
        if item_name is None:
            item_name = ""
        item_title = item[ "title" ]
        if item_title is None:
            item_title = ""
        print item_name + " (" + item_title + ")"

def cmd_login( args ):
    username = get_default_username()
    if "username" in args[ "options" ]:
        username = args[ "options" ][ "username" ]
        set_default_username( username )
    password = get_password()
    if "password" in args[ "options" ]:
        password = args[ "options" ][ "password" ]
    if username == "" or password =="":
        username = get_user_input( "Username: ", username )
        set_default_username( username )
    token = get_token()
    expires = get_expires()
    if token == "":
        url = portalUrl + "/sharing/rest/info"
        params = { }
        params[ "f" ] = "pjson"
        response = requests.get( url, params=params )
        tokenServicesUrl = response.json()[ "authInfo" ][ "tokenServicesUrl" ]
        if password == "":
            password = getpass.getpass( "Password: " )
        if password != "":
            params = { }
            params[ "username" ] = username
            params[ "password" ] = password
            params[ "referer" ] = portalUrl
            params[ "f" ] = "pjson"
            url = tokenServicesUrl
            response = requests.post( url, params=params )
            tokenInfo = response.json()
            if "error" in tokenInfo:
                print json.dumps( tokenInfo, indent=4, sort_keys=True )
                remove_password()
                return
            if "token" in tokenInfo:
                token = tokenInfo[ "token" ]
                set_token( token )
            if "expires" in tokenInfo:
                expires = tokenInfo[ "expires" ]
                set_expires( expires )
    if "forget" in args[ "options" ]:
        remove_password()
    if password !="":
        if "save" in args[ "options" ]:
            set_password( password )
    print "token_valid: " + elapsed_str( expires - time.time() * 1000.0 ) 

def cmd_logout( args ):
    username = get_default_username()
    if "username" in args[ "options" ]:
        username = args[ "options" ][ "username" ]
        set_default_username( username )
    remove_token()
    remove_expires()
    remove_password()

def cmd_mkdir( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print "mkdir what?"
        return
    folder_obj = crack_folder( args[ "parameters" ][1] )
    folder_title = folder_obj[ "folder_title" ]
    folder_id = folder_obj[ "folder_id" ]
    if folder_id != "":
        print "mkdir: " + folder_title + ": Cannot create directory. It already exists."
        return
    url = portalUrl + "/sharing/rest/content/users/" + username + "/createFolder"
    params = { }
    params[ "title" ] = folder_title
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.post( url, params=params )
    print json.dumps( response.json(), indent=4, sort_keys=True )

def cmd_rm( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print "rm what?"
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print "rm: " + item_path + ": No such directory."
        return
    item_title = item_obj[ "item_title" ]
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        item_path = item_obj[ "item_path" ]
        print "rm: " + item_path + ": No such item."
        return
    url = portalUrl + "/sharing/rest/content/users/" + username
    if folder_id != "":
        url = url + "/" + folder_id
    url = url + "/items/" + item_id + "/delete"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.post( url, params=params )
    print json.dumps( response.json(), indent=4, sort_keys=True )

def cmd_rmdir( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print "rmdir what?"
        return
    folder_obj = crack_folder( args[ "parameters" ][1] )
    folder_title = folder_obj[ "folder_title" ]
    folder_id = folder_obj[ "folder_id" ]
    if folder_id == "":
        print "rmdir: " + folder_title + ": No such directory."
        return
    url = portalUrl + "/sharing/rest/content/users/" + username + "/" + folder_id + "/delete"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.post( url, params=params )
    print json.dumps( response.json(), indent=4, sort_keys=True )

def cmd_update( args ):
    token = get_token_ex( args )
    if token == "":
        print "Not logged in"
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print "update what?"
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print "update: " + item_path + ": No such directory."
        return
    item_title = item_obj[ "item_title" ]
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        url = portalUrl + "/sharing/rest/content/users/" + username
        if folder_id != "":
            url = url + "/" + folder_id
        url = url + "/addItem"
        params = { }
        params[ "type" ] = "Code Sample"
        params[ "token" ] = token
        params[ "title" ] = item_title
        params[ "tags" ] = "code, sample"
        params[ "f" ] = "pjson"
        for key in args[ "options" ]:
            if passthru_option( key ):
                params[key] = args[ "options" ][key]
        mime_type = "application/octet-stream"
        files = { }
        files[ "file" ] = ( item_title, sys.stdin, mime_type )
        response = requests.post( url, params=params, files=files )
        print json.dumps( response.json(), indent=4, sort_keys=True )
        return
    url = portalUrl + "/sharing/rest/content/users/" + username
    if folder_id != "":
        url = url + "/" + folder_id
    url = url + "/items/" + item_id + "/update"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    for key in args[ "options" ]:
        if passthru_option( key ):
            params[key] = args[ "options" ][key]
    mime_type = "application/octet-stream"
    files = { }
    files[ "file" ] = ( item_title, sys.stdin.read(), mime_type )
    response = requests.post( url, params=params, files=files )
    print json.dumps( response.json(), indent=4, sort_keys=True )

load_settings()

args = parse_args()
parameters = args[ "parameters" ]
if len(parameters) == 0:
    cmd_login( args )
elif parameters[0] == "ls":
    cmd_ls( args )
elif parameters[0] == "cat":
    cmd_cat( args )
elif parameters[0] == "info":
    cmd_info( args )
elif parameters[0] == "login":
    cmd_login( args )
elif parameters[0] == "logout":
    cmd_logout( args )
elif parameters[0] == "mkdir":
    cmd_mkdir( args )
elif parameters[0] == "rm":
    cmd_rm( args )
elif parameters[0] == "rmdir":
    cmd_rmdir( args )
elif parameters[0] == "update":
    cmd_update( args )

