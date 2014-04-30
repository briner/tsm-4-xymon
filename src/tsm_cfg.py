from __future__ import print_function
import re
import datetime
NOW=datetime.datetime.now()

DATE_RELEVANT=datetime.datetime.now()-datetime.timedelta(hours=+24*4)

#
# spicify the time after that a red errors become yellow
RED_2_YELLOW_DATETIME=datetime.datetime(NOW.year, NOW.month, NOW.day)-datetime.timedelta(hours=+1)

#
# specify the time for which a filespace not beeing backup get yellow or red
FILESPACE_TIME_2_GET_YELLOW=datetime.timedelta(1,0,0,0,0,12)   # more than one day and half
FILESPACE_TIME_2_GET_RED=datetime.timedelta(2,0,0,0,0,12)      # more than two day and half

#
# specify the time for which the whole process of dsmc get yellow or red
# this time is taken from "Elapsed processing time" as mentionned in "SCHEDULEREC STATUS"
MAX_TIME_TO_BACKUP_YELLOW=datetime.timedelta(hours=+6) 
MAX_TIME_TO_BACKUP_RED=datetime.timedelta(hours=+6) 

#
# specify the mountpoint which translate to filespace that should not be monitored
RE_MOUNTPOINT_NOT_MONITORED=[#re.compile("/system/volatile")
                            ]
#
# lists errors ANS??? that should not become red or yellow
LIST_ERROR_CODE_DISABLED=[
                          #"ANS1898I"   # TSM has processed the specified number of files.
                          "ANS1696W"   # Objects were excluded from backup because the file system file-system-name is excluded from backup or archive processing.
                          ,"ANS1115W"   # EXCLUDE.DIR You can not back up, archive, or migrate files that are excluded.
                          ,"ANS1149E"   # EXCLUDE.FS  You can not back up, archive, or migrate files that are excluded.
                          ,"ANS1809W"   # An session with the TSM server has been disconnected. An attempt will be made to reestablish the connection.
                          #,"ANS2200I"   # Filling cache (memory efficient).
                          #,"ANS2201I"   # Inspecting cache (memory efficient).
                          ,"ANS2820E"   # An interrupt has occurred. The current operation will end and the client will shut down.
                          #,"ANS1483I"   # Schedule log pruning started.
                          #,"ANS1484I"  # Schedule log pruning finished successfully.
                          ]

#
# lists errors ANS??? that should not displayed
LIST_ERROR_CODE_NOT_DISPLAYED=["ANS1696W"   # Objects were excluded from backup because the file system file-system-name is excluded from backup or archive processing.
                              ,"ANS1898I"   # TSM has processed the specified number of files.
                              ,"ANS1483I"   # Schedule log pruning started.
                              ,"ANS1484I"  # Schedule log pruning finished successfully.
                              ]

#
# list message that should not monitored.
# eg:
#   (1) ... ANS1228E Sending of object '/zones/zjeannino4_pool/zjeannino4/root/system/volatile/unige_zfs_rpool.lock' failed
#   (2) ... ANS1802E Incremental backup of '/zones/zjeannino4_pool/zjeannino4/root/system/volatile' finished with 1 failure
RE_MSG_NOT_MONITORED=[re.compile("'.*/system/volatile/unige\S+.lock'") # (1)
                     ,re.compile("'.*/system/volatile' finished with [123] failure") # (2)
                    ]


#
# hack: brings some code
def get_color_isdisplayed_of_entry_dsmcsched(date_time, error_code, msg):
    '''this function must return a True/false which is calculated with:
    - error_code : the error code returned by tsm (such as: ANS1898I")
    - the message after the error_code.
    - date_time: datetime object moment of the entry in dsmsched.log
    the error_code could be an empty string'''
    def datetime_2_color(date_time):
        if date_time > RED_2_YELLOW_DATETIME:
            return "red"
        else:
            return "yellow"
    if error_code in LIST_ERROR_CODE_NOT_DISPLAYED:
        return ("blue", False)
    if date_time < DATE_RELEVANT:
        return ("blue", False)
    if msg.find("No schedule returned from server.") !=-1:
        return (datetime_2_color(date_time), True)
    if not error_code:
        return ("green", False)
    if error_code in LIST_ERROR_CODE_DISABLED:
        return ("blue", True)
    else:
        for re_inst in RE_MSG_NOT_MONITORED:
            if re_inst.search(msg):
                return ("blue", True)
        if error_code[-1] == "I":
            return ("green", True)
        elif error_code[-1] == "W":
            return ("yellow", True)
        else:
            return (datetime_2_color(date_time), True)
