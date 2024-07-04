import os
import time
import mss
import cv2
import socket
import sys
import struct
import math
import random
import win32api as wapi
import win32api
import win32gui
import win32process
import ctypes
from ctypes  import *
from pymem   import *

import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

import numpy as np
import matplotlib.pyplot as plt

from key_input import key_check, mouse_check, mouse_l_click_check, mouse_r_click_check
from key_output import set_pos, HoldKey, ReleaseKey
from key_output import left_click, hold_left_click, release_left_click
from key_output import w_char, s_char, a_char, d_char, n_char, q_char
from key_output import ctrl_char, shift_char, space_char
from key_output import r_char, one_char, two_char, three_char, four_char, five_char
from key_output import p_char, e_char, c_char_, t_char, cons_char, ret_char

from screen_input_old import grab_window
from config import *
from meta_utils import *

# first make sure offset list is reset (after csgo updates may shift about)
if True:
    print('updating offsets')
    offsets_old = requests.get('https://raw.githubusercontent.com/frk1/hazedumper/master/csgo.toml').text
    print(';;;;;;;')
    print(offsets_old)
    print('-------')
    offsets = requests.get('https://github.com/sezzyaep/CS2-OFFSETS/blob/main/offsets.yaml').text
    print(offsets)
    print('000000000')
    del requests
    update_offsets(offsets)

from dm_hazedumper_offsets import *

save_name = 'dm_test_' # stub name of file to save as
folder_name = '/new_train_model/'
# starting_value = get_highest_num(save_name, folder_name)+1 # set to one larger than whatever found so far
starting_value = 1

is_show_img = False

# now find the requried process and where two modules (dll files) are in RAM
hwin_csgo = win32gui.FindWindow(0, ('Counter-Strike 2'))
if(hwin_csgo):
    pid=win32process.GetWindowThreadProcessId(hwin_csgo)
    handle = pymem.Pymem()
    handle.open_process_from_id(pid[1])
    csgo_entry = handle.process_base
else:
    print('CS2 wasnt found')
    os.system('pause')
    sys.exit()

# now find two dll files needed
list_of_modules=handle.list_modules()
while(list_of_modules!=None):
    tmp=next(list_of_modules)
    # used to be client_panorama.dll, moved to client.dll during 2020
    if(tmp.name=="client.dll"):
        print('found client.dll')
        off_clientdll=tmp.lpBaseOfDll
        break
list_of_modules=handle.list_modules()
while(list_of_modules!=None):
    tmp=next(list_of_modules)
    if(tmp.name=="engine2.dll"):
        print('found engine.dll')
        off_enginedll=tmp.lpBaseOfDll
        break

# not sure what this bit does? sets up reading/writing from RAM I guess
OpenProcess = windll.kernel32.OpenProcess
CloseHandle = windll.kernel32.CloseHandle
PROCESS_ALL_ACCESS = 0x1F0FFF
game = windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, 0, pid[1])


SAVE_TRAIN_DATA = True
IS_PAUSE = False # pause saving of data
n_loops = 0 # how many frames looped 
training_data=[]
img_small = grab_window(hwin_csgo, game_resolution=csgo_game_res, SHOW_IMAGE=False)
print('starting loop, press q to quit...')
queue = multiprocessing.Queue()
server = ListenerServer(("127.0.0.1", 3000), PostHandler, multiprocessing.Queue())

onetime = True
while True:
    loop_start_time = time.time()
    n_loops += 1
    

    print(n_loops)
    keys_pressed = key_check()
    print(keys_pressed)
    if 'Q' in keys_pressed:
        # exit loop
        print('exiting...')
        break

    curr_vars={}

    # grab address of ME = player, and see what observation mode I'm in
    player = read_memory(game,(off_clientdll + dwLocalPlayer), "i")
    curr_vars['obs_mode'] = read_memory(game,(player + m_iObserverMode),'i')

    # --- get GSI info
    print('getting server')
    server.handle_request()
    # server = MyServer(('localhost', 3000), MyRequestHandler)

    print('got server')
    # server.handle_request()
    # print(server)
    if server.data_all == None: #the server haven't get the data yet
        continue 
    # need some logic to automate when record the game or not
    # first let's not proceed if the map is loading
    if 'map' not in server.data_all.keys():
        print('not recording, map not in keys')
        time.sleep(5)
        continue
    else:
        print('recording')
        print(curr_vars)
        print('----')
        # print(server.data_all)


    if server.data_all['map']['phase']!='live': # and server.data_all['map']['phase']!='warmup':
        print('not recording, not live')
        # seem to need to restart the gsi connection between each game
        server.server_close()
        server = MyServer(('localhost', 3000), MyRequestHandler)
        server.handle_request()

        while server.data_all['map']['phase']!='live' and server.data_all['map']['phase']!='warmup':
            print('not recording, waiting to go live')
            time.sleep(15)

            # try to join terrorist team
            HoldKey(one_char)
            time.sleep(0.5)
            ReleaseKey(one_char)

            # try to take a step
            HoldKey(w_char)
            time.sleep(0.5)
            ReleaseKey(w_char)

            server.server_close()
            server = MyServer(('localhost', 3000), MyRequestHandler)
            server.handle_request()
            if 'map' not in server.data_all.keys(): # hacky way to avoid this triggering failure
                server.data_all['map']={}
                server.data_all['map']['phase']='dummy'
            print(server.data_all['map'])
        print('game went live,', time.time())
        # time_start_game = time.time()
        print('using console to spectate')
        time.sleep(3)
        for c in [cons_char,s_char,p_char,e_char,c_char_,t_char,a_char,t_char,e_char,ret_char,cons_char,two_char]:
            # type spectate
            time.sleep(0.25)
            HoldKey(c)
            ReleaseKey(c)

        # switch to first person view
        time.sleep(2)
        player = read_memory(game,(off_clientdll + dwLocalPlayer), "i")
        obs_mode_i = read_memory(game,(player + m_iObserverMode),'i')
        while obs_mode_i in [5,6]:
            print(obs_mode_i)
            HoldKey(space_char)
            time.sleep(0.1)
            ReleaseKey(space_char)
            time.sleep(2)
            obs_mode_i = read_memory(game,(player + m_iObserverMode),'i')
        continue

    # don't proceed if not observing from first person, or something wrong with GSI
    if 'team' not in server.data_all['player'].keys() or curr_vars['obs_mode'] in [5,6]:
        print('not recording')
        time.sleep(5)
        continue

    # sort through GSI data package and get useful info
    curr_vars['gsi_team'] = server.data_all['player']['team']
    curr_vars['gsi_health'] = server.data_all['player']['state']['health']
    curr_vars['gsi_kills'] = server.data_all['player']['match_stats']['kills']
    curr_vars['gsi_deaths'] = server.data_all['player']['match_stats']['deaths']
    curr_vars['gsi_weapons'] = server.data_all['player']['weapons']

    # get GSI active weapon
    curr_vars['found_active']=False
    for w in curr_vars['gsi_weapons']:
        if curr_vars['gsi_weapons'][w]['state'] != 'holstered': # can be holstered, active, reloading
            curr_vars['gsi_weap_active'] = curr_vars['gsi_weapons'][w]
            curr_vars['found_active']=True

            # get active ammo - edge cases are knife and 'weapon_healthshot'
            if 'type' in curr_vars['gsi_weapons'][w].keys(): # this doesn't happen if taser, but still has ammo_clip
                if curr_vars['gsi_weapons'][w]['type'] == 'Knife' or curr_vars['gsi_weapons'][w]['type'] == 'StackableItem':
                    curr_vars['gsi_ammo'] = -1
                else:
                    curr_vars['gsi_ammo'] = curr_vars['gsi_weap_active']['ammo_clip']
            else:
                curr_vars['gsi_ammo'] = curr_vars['gsi_weap_active']['ammo_clip']

    # --- get RAM info
    if curr_vars['obs_mode']==4: # figure out which player I'm observing
        obs_handle = read_memory(game,(player + m_hObserverTarget),'i')
        obs_id = (obs_handle & 0xFFF)
        obs_address = read_memory(game,off_clientdll + dwEntityList + ((obs_handle & 0xFFF)-1)*0x10, "i")
    else: # else if not observing, just use me as player
        obs_address = player
        obs_id=None
        
    # get player info
    # curr_vars['obs_health'] = read_memory(game,(obs_address + m_iHealth), "i")
    # curr_vars['obs_fov'] = read_memory(game,(obs_address + m_iFOVStart),'i') # m_iFOVStart m_iFOV
    # curr_vars['obs_scope'] = read_memory(game,(obs_address + m_bIsScoped),'b')

    # get player position, x,y,z and height
    curr_vars['localpos1'] = read_memory(game,(obs_address + m_vecOrigin), "f") #+ read_memory(game,(vecorigin + m_vecViewOffset + 0x104), "f")
    curr_vars['localpos2'] = read_memory(game,(obs_address + m_vecOrigin + 0x4), "f") #+ read_memory(game,(vecorigin + m_vecViewOffset + 0x108), "f")
    curr_vars['localpos3'] = read_memory(game,(obs_address + m_vecOrigin + 0x8), "f") #+ read_memory(game,(obs_address + 0x10C), "f")
    curr_vars['height'] = read_memory(game,(obs_address + m_vecViewOffset + 0x8), "f") # this returns z height of player, goes between 64.06 and 46.04
    print(curr_vars)
    # get player velocity, x,y,z
    curr_vars['vel_1'] = read_memory(game,(obs_address + m_vecVelocity), "f") 
    curr_vars['vel_2'] = read_memory(game,(obs_address + m_vecVelocity + 0x4), "f")
    curr_vars['vel_3'] = read_memory(game,(obs_address + m_vecVelocity + 0x8), "f")
    curr_vars['vel_mag'] = np.sqrt(curr_vars['vel_1']**2 + curr_vars['vel_2']**2 )

    # get player view angle, something like yaw and vertical angle
    enginepointer = read_memory(game,(off_enginedll + dwClientState), "i")
    curr_vars['viewangle_vert'] = read_memory(game,(enginepointer + dwClientState_ViewAngles), "f")
    curr_vars['viewangle_xy'] = read_memory(game,(enginepointer + dwClientState_ViewAngles + 0x4), "f")

    # zvert_rads is 0 when staring at ground, pi when starting at ceiling
    curr_vars['zvert_rads'] = (-curr_vars['viewangle_vert'] + 90)/360 * (2*np.pi)
    
    # xy_rad is 0 and 2pi when pointing true 'north', increasing from 0 to 2pi as turn clockwise, so pi when point south
    if curr_vars['viewangle_xy']<0:
        xy_deg = -curr_vars['viewangle_xy']
    elif curr_vars['viewangle_xy']>=0:
        xy_deg = 360-curr_vars['viewangle_xy']
    curr_vars['xy_rad'] = xy_deg/360*(2*np.pi)

    # print('mouse xy_rad',np.round(curr_vars['xy_rad'],2), end='\r')
    # print('obs_hp',curr_vars['obs_health'],'gsi_hp',curr_vars['gsi_health'], curr_vars['gsi_team'], curr_vars['gsi_kills'], curr_vars['obs_fov'], 'mouse xy_rad',np.round(curr_vars['xy_rad'],2), end='\r')

    # get velocity relative to direction facing, 0 or 2pi if running directly forwards, pi if directly backwards, pi/2 for right
    vel_x = curr_vars['vel_1']
    vel_y = -curr_vars['vel_2']

    if vel_y>0 and vel_x>0:
        vel_theta_abs = np.arctan(vel_y/vel_x)
    elif vel_y>0 and vel_x<0:
        vel_theta_abs = np.pi/2 + np.arctan(-vel_x/vel_y)
    elif vel_y<0 and vel_x<0:
        vel_theta_abs = np.pi + np.arctan(-vel_y/-vel_x)
    elif vel_y<0 and vel_x>0:
        vel_theta_abs = 2*np.pi - np.arctan(-vel_y/vel_x)
    elif vel_y==0 and vel_x==0:
        vel_theta_abs=0
    elif vel_y==0 and vel_x>0:
        vel_theta_abs=0
    elif vel_y==0 and vel_x<0:
        vel_theta_abs=np.pi
    elif vel_x==0 and vel_y>0:
        vel_theta_abs=np.pi/2
    elif vel_x==0 and vel_y<0:
        vel_theta_abs=2*np.pi*3/4
    else:
        vel_theta_abs = 0
    curr_vars['vel_theta_abs'] = vel_theta_abs

    # get weapon info
    weapon_handle = read_memory(game,obs_address + m_hActiveWeapon, "i")
    weapon_address = read_memory(game,off_clientdll + dwEntityList + ((weapon_handle & 0xFFF)-1)*0x10, "i")
    curr_vars['itemdef'] = read_memory(game,(weapon_address + m_iItemDefinitionIndex), "i") 
    curr_vars['ammo_active'] = read_memory(game,(weapon_address + m_iClip1), "i")

    try:
        print('obs_hp',curr_vars['obs_health'],'gsi_hp',curr_vars['gsi_health'], curr_vars['gsi_team'], curr_vars['gsi_kills'],'mouse xy_rad',np.round(curr_vars['viewangle_xy'],2), 'zvert_rads', curr_vars['viewangle_vert'], 'obs_mode', curr_vars['obs_mode'], 'ammo', curr_vars['ammo_active'], curr_vars['gsi_ammo'], curr_vars['localpos1'], curr_vars['vel_1'], curr_vars['vel_2'])
    except:
        print('not printing')

    # save image and action
    timeleft=9999
    if 'phase_countdowns' in server.data_all.keys():
        if 'phase_ends_in' in server.data_all['phase_countdowns'].keys():
            timeleft = float(server.data_all['phase_countdowns']['phase_ends_in'])
        # trying to avoid that early minute of play to figure out who's good
    # print(timeleft)
    # if SAVE_TRAIN_DATA and not IS_PAUSE and timeleft < 540:
    if SAVE_TRAIN_DATA and not IS_PAUSE: ## not if capturing bot behaviour!
        info_save = curr_vars
        training_data.append([img_small,curr_vars])
        # training_data.append([[],curr_vars]) # if don't want to save image, eg tracking around map
        if len(training_data) % 100 == 0:
            print('training data collected:', len(training_data))

        if len(training_data) >= 1000:
            # save about every minute
            file_name = folder_name+save_name+'{}.npy'.format(starting_value)
            np.save(file_name,training_data)
            print('SAVED', starting_value)
            training_data = []
            starting_value += 1

    if n_loops%200==0 or curr_vars['gsi_health'] == 0:

        HoldKey(one_char) # chooses top scoring player in server
        time.sleep(0.03)
        ReleaseKey(one_char)


    # grab image
    if SAVE_TRAIN_DATA:
        img_small = grab_window(hwin_csgo, game_resolution=csgo_game_res, SHOW_IMAGE=is_show_img)
        # we put the image grab last as want the time lag to match when
        # will be running fwd pass through NN

    wait_for_loop_end(loop_start_time, loop_fps, n_loops, is_clear_decals=True)

