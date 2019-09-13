#!/usr/bin/python

import os, sys, requests, json, getpass, time, math, re

settings_path = os.path.expanduser( "~/.config/Esri/agtool/agtool.json" )
settings = { }

portalUrl = "https://www.arcgis.com"

k_default_username = "default_username"
k_password = "password"
k_token = "token"
k_expires = "expires"

args = { }

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

def hash_user_key( username, key):
    if username == "":
        username = get_default_username()
    return username + "_" + key

def get_user_settings( key, defaultValue="", username="" ):
    return get_settings( hash_user_key( username, key ), defaultValue )

def set_user_settings( key, value, username="" ):
    set_settings( hash_user_key( username, key ), value )

def remove_user_settings( key, username="" ):
    remove_settings( hash_user_key( username, key ) )

def get_token():
    token = get_user_settings( k_token )
    if token == "":
        return token
    expires = get_expires()
    if time.time() * 1000.0 >= expires:
        return ""
    return token

def get_token_ex():
    global args
    username = get_default_username()
    if "username" in args[ "options" ]:
        username = args[ "options" ][ "username" ]
        set_default_username( username )
    token = get_token()
    if token == "":
        _login()
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

def skip_option( option ):
    if option == "username":
        return True
    if option == "password":
        return True
    if option == "save":
        return True
    if option == "forget":
        return True
    if option == "out":
        return True
    if option == "file":
        return True
    if option == "thumbnail":
        return True
    return False

def unary_option( option ):
    if option == "save":
        return True
    if option == "forget":
        return True
    return False

def parse_args():
    global args
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

def get_user_input( prompt, defaultValue="" ):
    if defaultValue != "":
        prompt = prompt + "[ " + defaultValue + " ]: "
    value = input( prompt ) if sys.version_info >= (3,0) else raw_input( prompt )
    return value if value != "" else defaultValue

def print_error( msg ):
    sys.stdout.write( msg + "\n" )

def print_obj( obj ):
    if "out" in args[ "options" ]:
        with open( args[ "options"][ "out" ], "wb" ) as out:
            out.write( json.dumps( obj, indent=4, sort_keys=True ) + "\n" )
    else:
        sys.stdout.write( json.dumps( obj, indent=4, sort_keys=True ) + "\n" )

def print_text( text ):
    sys.stdout.write( text + "\n" )

def elapsed_str( ms ):
    sec = math.trunc( ms / 1000.0 )
    if sec < 60:
        return str(sec) + " seconds"
    min = math.trunc( sec / 60.0 )
    return str(min) + " minutes"

def get_folder_id( folder_title ):
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." );
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    if "folders" not in response.json():
        print_obj( response.json() )
        return ""
    for folder in response.json()[ "folders" ]:
        if folder[ "title" ] == folder_title:
            return folder[ "id" ]
    return ""

def get_item_id( item_title, folder_id=""):
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
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

def cmd_cat():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    if len( args[ "parameters" ] ) < 1:
        print_error( "cat what?" )
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "cat: " + item_path + ": No such folder." )
        return
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "cat: " + item_path + ": No such item." )
        return
    url = portalUrl + "/sharing/rest/content/items/" + item_id + "/data"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params, stream=True )
    # print response.text
    # sys.stdout.write( response.text )
    response.raw.decode_content = True
    if "out" in args[ "options" ]:
        with open( args[ "options"][ "out" ], "wb" ) as out:
            out.write( response.raw.read() )
    else:
        if sys.version_info >= (3,0):
            sys.stdout.buffer.write( response.raw.read() )
        else:
            sys.stdout.write( response.raw.read() )
        sys.stdout.flush()

def cmd_info():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    if len( args[ "parameters" ] ) < 1:
        print_error( "info what?" )
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "info: " + item_path + ": No such folder." )
        return
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "info: " + item_path + ": No such item." )
        return
    url = portalUrl + "/sharing/rest/content/items/" + item_id
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    print_obj( response.json() )

def cmd_ls():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    url = portalUrl + "/sharing/rest/content/users/" + username
    folder_id = ""
    if len( args[ "parameters" ] ) >= 2:
        folder_obj = crack_folder( args[ "parameters" ][1] )
        folder_id = folder_obj[ "folder_id" ]
        folder_title = folder_obj[ "folder_title" ]
        if folder_title != "":
            if folder_id == "":
                print_error( "ls: " + folder_title + ": No such folder." )
                return
            url = url + "/" + folder_id
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.get( url, params=params )
    result = ""
    if "folders" in response.json():
        for folder in response.json()[ "folders" ]:
            result = result + folder[ "title" ] + "/"  + "\n"
    for item in response.json()[ "items" ]:
        item_name = item[ "name" ]
        if item_name is None:
            item_name = ""
        item_title = item[ "title" ]
        if item_title is None:
            item_title = ""
        item_access = item[ "access" ]
        item_owner = item[ "owner" ]
        item_size = item[ "size" ]
        item_size_text = str( item_size )
        item_modified = item[ "modified" ]
        item_modified_text = time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime( item_modified / 1000.0 ) ) 
        # result = result + item_name + " (" + item_title + ")" + "\n"
        # result = result + item_access + " " + item_owner + " " + item_size_text + " " + item_modified_text + " " + item_name + " (" + item_title + ")" + "\n"
        result = result + item_access.ljust(10)
        result = result + " " + item_owner.ljust(10)
        result = result + " " + item_size_text.rjust(10)
        result = result + " " + item_modified_text.ljust(20)
        result = result + " " + item_name
        result = result + " (" + item_title + ")"
        result = result + "\n"
    print_text( result )

def _login():
    global args
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
                print_obj( tokenInfo )
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

def cmd_login():
    _login()
    token = get_token()
    if token == "":
        return
    expires = get_expires()
    sys.stdout.write( "Current token valid for " + elapsed_str( expires - time.time() * 1000.0 ) + "\n" )

def cmd_logout():
    global args
    username = get_default_username()
    if "username" in args[ "options" ]:
        username = args[ "options" ][ "username" ]
        set_default_username( username )
    remove_token()
    remove_expires()
    remove_password()

def cmd_mkdir():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print_error( "mkdir what?" )
        return
    folder_obj = crack_folder( args[ "parameters" ][1] )
    folder_title = folder_obj[ "folder_title" ]
    folder_id = folder_obj[ "folder_id" ]
    if folder_id != "":
        print_error( "mkdir: " + folder_title + ": Cannot create directory. It already exists." )
        return
    url = portalUrl + "/sharing/rest/content/users/" + username + "/createFolder"
    params = { }
    params[ "title" ] = folder_title
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.post( url, params=params )
    print_obj( response.json() )

def cmd_rm():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print_error( "rm what?" )
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "rm: " + item_path + ": No such folder." )
        return
    item_title = item_obj[ "item_title" ]
    item_id = item_obj[ "item_id" ]
    if item_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "rm: " + item_path + ": No such item." )
        return
    url = portalUrl + "/sharing/rest/content/users/" + username
    if folder_id != "":
        url = url + "/" + folder_id
    url = url + "/items/" + item_id + "/delete"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.post( url, params=params )
    print_obj( response.json() )

def cmd_rmdir():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print_error( "rmdir what?" )
        return
    folder_obj = crack_folder( args[ "parameters" ][1] )
    folder_title = folder_obj[ "folder_title" ]
    folder_id = folder_obj[ "folder_id" ]
    if folder_id == "":
        print_error( "rmdir: " + folder_title + ": No such folder." )
        return
    url = portalUrl + "/sharing/rest/content/users/" + username + "/" + folder_id + "/delete"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    response = requests.post( url, params=params )
    print_obj( response.json() )

def get_mime_type( filename ):
    mime_type = "application/octet-stream"
    if filename.endswith( (".jpg", ".jpeg") ):
        return "image/jpeg"
    if filename.endswith( ".png" ):
        return "image/png"
    if filename.endswith( ".gif" ):
        return "image/gif"
    return mime_type

def get_file_stream( filepath, mime_type = "", filename = ""):
    if filename == "":
        filename = os.path.basename( filepath )
    if mime_type == "":
        mime_type = get_mime_type( filename )
    stream = sys.stdin if filepath == "-" else open( filepath, "rb" )
    print "filename: " + filename
    print "mime_type: " + mime_type
    return ( filename, stream, mime_type )

def get_files( args, item_title = "" ):
    files = { }
    if "file" in args[ "options" ]:
        files[ "file" ] = get_file_stream( args[ "options" ][ "file" ], "", item_title )
    if "thumbnail" in args[ "options" ]:
        files[ "thumbnail" ] = get_file_stream( args[ "options" ][ "thumbnail" ] )
    return files

def cmd_update():
    global args
    token = get_token_ex()
    if token == "":
        print_error( "Not logged in." )
        return
    username = get_default_username()
    if len( args[ "parameters" ] ) < 1:
        print_error( "update what?" )
        return
    item_obj = crack_item( args[ "parameters" ][1] )
    folder_title = item_obj[ "folder_title" ]
    folder_id = item_obj[ "folder_id" ]
    if folder_title != "" and folder_id == "":
        item_path = item_obj[ "item_path" ]
        print_error( "update: " + item_path + ": No such folder." )
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
            if not skip_option( key ):
                params[key] = args[ "options" ][key]
        files = get_files( args, item_title )
        response = requests.post( url, params=params, files=files )
        print_obj( response.json() )
        return
    url = portalUrl + "/sharing/rest/content/users/" + username
    if folder_id != "":
        url = url + "/" + folder_id
    url = url + "/items/" + item_id + "/update"
    params = { }
    params[ "token" ] = token
    params[ "f" ] = "pjson"
    for key in args[ "options" ]:
        if not skip_option( key ):
            params[key] = args[ "options" ][key]
    files = get_files( args, item_title )
    response = requests.post( url, params=params, files=files )
    print_obj( response.json() )

load_settings()

parse_args()
parameters = args[ "parameters" ]
if len(parameters) == 0:
    cmd_login( )
elif parameters[0] == "ls":
    cmd_ls( )
elif parameters[0] == "cat":
    cmd_cat( )
elif parameters[0] == "info":
    cmd_info( )
elif parameters[0] == "login":
    cmd_login( )
elif parameters[0] == "logout":
    cmd_logout( )
elif parameters[0] == "mkdir":
    cmd_mkdir( )
elif parameters[0] == "rm":
    cmd_rm( )
elif parameters[0] == "rmdir":
    cmd_rmdir( )
elif parameters[0] == "update":
    cmd_update( )

