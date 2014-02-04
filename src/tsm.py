#!/usr/bin/python
# -*- coding: utf-8 -*-
'''Displays each ZFS pool name with capacity and status'''

# 06.12.2012 cED
#            - initial release

from __future__ import print_function

import os, sys
import datetime
import subprocess
import re
from optparse import OptionParser
import glob

import tsm_cfg


###############################################################################
# DEFINITION

NOW=datetime.datetime.now()
HOBBIT_TESTNAME="bkp"
RE_STR_DATETIME="\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
RE_SCHEDULERC_STATUS=re.compile(r"(--- SCHEDULEREC STATUS BEGIN.*--- SCHEDULEREC STATUS END)", re.DOTALL)
RE_SCHEDULERC_STATUS=re.compile('--- SCHEDULEREC STATUS BEGIN[^\n]*((?:\n[^\n]+){15})\n[^\n]* --- SCHEDULEREC STATUS END', re.DOTALL)
RE_STR_ELAPSED_PROCESSING_TIME="(?P<datetime_entry>%s) Elapsed processing time:\s+(?P<elapsed_processing_timedelta>\S+)" % RE_STR_DATETIME
RE_ELAPSED_PROCESSING_TIME=re.compile(RE_STR_ELAPSED_PROCESSING_TIME)

TERMINAL_OR_WEB="terminal"
#
# definition DEBUG
DEBUG=["dsmc_query_filesystem"]
DEBUG=[]

#### SMALL UTILITY
def print_debug(*args):
    name=args[0]
    if name in DEBUG:
        try:
            args=[arg.replace('\\n','\n%s ' % name) for arg in args[1:]]
        except:
            args=[repr(arg).replace('\\n','\n%s ' % name) for arg in args[1:]]
        print( name+' '+' '.join(args) )

def is_launched_within_xymon():
   '''
   if this script was launched within xymon, then the environment variable BB is set.
   '''
   return bool(os.environ.get('BB', None))

class Color(object):
  lcolor=["blue", 'green', 'yellow', 'red']
  def __init__(self, color):
    self.color=color
  def __str__(self):
    if TERMINAL_OR_WEB=="terminal":
      return self.color
    return "&"+self.color
  def __len__(self):
    if TERMINAL_OR_WEB=="terminal":
      return len(self.color)
    else:
      return 1
  def add(self, color_2):
    if isinstance(color_2, Color):
      color_2=color_2.color
    iself=self.lcolor.index(self.color)
    icolor_2=self.lcolor.index(color_2)
    if iself < icolor_2:
        self.color=color_2

def getSizeOfList(l):
   return map(lambda x:len(x), l)

def listlist2nicestr(ll):
   outputFormat=[]
   if list != type(ll):
      return 'this is not a list'
   if len(ll)==0:
      return ''
   for i in range(len(ll)):
      if list != type(ll[i]):
         return 'this list in not constitued of list'
      #lelem=lelem+ll[i]
      if 0 == i:
         refSizeList=getSizeOfList(ll[i])
         refLenList=len(ll[i])
      else:
         if refLenList != len(ll[i]):
            return 'error all the list should be the same lenght'
         sizeList=getSizeOfList(ll[i])
         for j in range(refLenList):
            if refSizeList[j]< sizeList[j]:
               refSizeList[j] = sizeList[j]
   outputFormatLine=u' '.join( map(lambda x:"%-"+unicode(x)+'s', refSizeList) )
   output=u''
   for l in ll:
      try:
         output+=outputFormatLine%tuple(l)+u'\n'
      except UnicodeDecodeError, qq:
         print(str(type(output)), output)
         print(l)
         print(str(type (l[1])),  l[1])
         print(str(type (ll[13][1][0])), ll[13][1][0])
         raise qq
   return output[:-1]

def cmpAlphaNum(str1,str2):
    if ( not str1 )or( not str2 ):
        return cmp(str1, str2)
    str1=str1.lower()
    str2=str2.lower()
    ReSplit='(\d+)'
    str1=re.split(ReSplit,str1)
    str2=re.split(ReSplit,str2)
    if( ''==str1[0] ):
        str1.remove('')
    if( ''==str1[len(str1)-1] ):
        str1.remove('')
    if( ''==str2[0] ):
        str2.remove('')
    if( ''==str2[len(str2)-1] ):
        str2.remove('')
    for i in range( min( len(str1),len(str2) ) ):
        try:
            tmp=int(str1[i])
            str1[i]=tmp
        except:ValueError
        try:
            tmp=int(str2[i])
            str2[i]=tmp
        except:ValueError
        if( str1[i]==str2[i] ):
            continue
        if (str1[i]>str2[i]):
            return 1
        else:
            return -1
    return cmp(len(str1),len(str2))

##################################
def dsmc_query_filesystem():
    inst_cmd="sudo /usr/bin/dsmc q fi -time=1 -date=3"
    print_debug("dsmc_query_filesystem", "dsmc_query_filesystem with cmd(%s):" % inst_cmd)
    proc=subprocess.Popen(inst_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd='/')
    lstdout=proc.stdout.readlines()
    lstderr=proc.stderr.readlines()
    proc.communicate()
    retcode=proc.wait()
    if retcode != 0:
        lmsg=['the cmd (%s) did not succeed' % inst_cmd]
        for line in lstdout:
            lmsg.append(' - stdout: %s' % line.rstrip())
        for line in lstderr:
            lmsg.append(' - stderr: %s' % line.rstrip())
        for msg in lmsg:
            print(msg)
        raise Exception( 'dsmc_query_filesystem problem')
    node_name=None
    lfilesystem=[]
    section_color=Color("green")
    for out in lstdout:
        if 0==out.find('Node Name: '):
            node_name=out.rstrip()[len('Node Name: '):]
        match=re.match('^\s*(\d+)\s+(\S+\s+\S+)\s+(\S+)\s+(\S+)\s*$', out)
        if match:
            number, last_incr_datetime_raw, fs_type, fs_name=match.groups()
            if last_incr_datetime_raw == "0000-00-00 00:00:00":
              last_incr_datetime=datetime.datetime(1,1,1)
            else:
              #1    03-12-2012 00:02:20   ZFS     /dolly/backup
              last_incr_datetime=datetime.datetime.strptime(last_incr_datetime_raw, '%Y-%m-%d %H:%M:%S')
            last_incr_delta=NOW-last_incr_datetime
            if last_incr_delta > datetime.timedelta(2,0,0,0,0,12 ) : # more than two day and half
                color=Color("red")
            elif last_incr_delta > datetime.timedelta(1,0,0,0,0,12 ) : # more than one day and half
                color=Color("yellow")
            else:
                color=Color("green")
            for re_not_mounted in tsm_cfg.RE_MOUNTPOINT_NOT_MONITORED:
              if re_not_mounted.search(fs_name):
                color=Color("blue")
            lfilesystem.append((color, number, last_incr_datetime, last_incr_delta, fs_type, fs_name))
            section_color.add(color)
    if not lfilesystem:
      section_color=Color("red")
    return (node_name, section_color, lfilesystem)


# print re.compile(r"(--- SCHEDULEREC STATUS BEGIN.*--- SCHEDULEREC STATUS END)", re.DOTALL).search(b).groups()

def read_dsmsched_log():
  import time
  lfndsmsched=glob.glob("/var/log/dsmsched.log.*")
  lfndsmsched.sort(cmpAlphaNum)
  if os.path.isfile("/var/log/dsmsched.log"):
    lfndsmsched.append("/var/log/dsmsched.log")
  last_processed_date=None
  len_date=len("2013-01-04 00:03:46")
  RE_DSMSCHED=re.compile("^(?P<date_time_str>%s)(?: (?P<error_code>ANS\d{4}[IWE]))? (?P<msg>.*)$" % RE_STR_DATETIME)
  lmap_color_datetime_errorcode_msg_fndsmsched=[]
  section_color=Color("green")
  did_matched_once=False
  #
  # read the messages
  for fndsmsched in reversed(lfndsmsched):
    fh=open(fndsmsched, 'r')
    long_line_cutted=[]
    for line in reversed(open(fndsmsched, 'r').readlines()):
      match=RE_DSMSCHED.search(line)
      if not match:
        long_line_cutted.append(line)
      else:
        did_matched_once=True
        date_time_str, error_code, msg=match.groups()
        if long_line_cutted:
          msg=msg+" "+" ".join(long_line_cutted)
          msg=msg.rstrip()
        long_line_cutted=[]
        date_time=datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        last_processed_date=date_time.date()
        color_str, isdisplayed=tsm_cfg.get_color_isdisplayed_of_entry_dsmcsched( date_time, error_code, msg)
        color=Color(color_str)
        if isdisplayed:
          section_color.add(color)
          lmap_color_datetime_errorcode_msg_fndsmsched.append((color, date_time, error_code, msg, fndsmsched))
    days_later=NOW-datetime.timedelta(hours=+24*4)
    # lmap_color_datetime_errorcode_msg_fndsmsched=filter(lambda x: "green" != x[0]
    #                                                    ,lmap_color_datetime_errorcode_msg_fndsmsched)
  #
  # search for SCHEDULEREC STATUS BEGIN
  last_datetime_schedulerc=None
  last_color_schedulerc=None
  lschedulerc=[]
  for fndsmsched in reversed(lfndsmsched):
    for block in RE_SCHEDULERC_STATUS.finditer(open(fndsmsched,"r").read()):
      datetime_block=None
      ltmp_schedulerc=[]
      # for entry in block.groups()[0].split("\n")[1:-1]:
      for entry in block.groups()[0][1:].split('\n'):
        match=RE_ELAPSED_PROCESSING_TIME.search(entry)
        if match:
          tmp_color_schdulerc=Color("green")
          hours, minutes, seconds=[int(elem) for elem in match.groupdict()["elapsed_processing_timedelta"].split(":")]
          datetime_block=datetime.datetime.strptime(match.groupdict()["datetime_entry"], '%Y-%m-%d %H:%M:%S')
          elapsed_time_processing=datetime.timedelta(hours=+hours, minutes=+minutes, seconds=+seconds)
          if elapsed_time_processing > datetime.timedelta( hours=+8):
            tmp_color_schdulerc=Color("yellow")
          if elapsed_time_processing > datetime.timedelta( hours=+20):
            tmp_color_schdulerc=Color("red")
          ltmp_schedulerc.append([tmp_color_schdulerc, entry])
        else:
          ltmp_schedulerc.append([" ", entry])
      if datetime_block:
        if not last_datetime_schedulerc:
          last_datetime_schedulerc=datetime_block
          lschedulerc=ltmp_schedulerc[:]
          last_color_schedulerc=tmp_color_schdulerc
        elif datetime_block > last_datetime_schedulerc:
          last_datetime_schedulerc=datetime_block
          lschedulerc=ltmp_schedulerc[:]
          last_color_schedulerc=tmp_color_schdulerc
  #
  #
  llmapsection_color_message=[]
  if not did_matched_once:
    section_color=Color("red")
    llmapsection_color_message.append([Color("red"), "check dsm.opt with options [DATEformat 3, TIMEformat 1, because no parsable log in all dsmsched.log* were matching(RE_DSMSCHED), ]"])
  # if not lmap_color_datetime_errorcode_msg_fndsmsched:
  #   section_color=Color("green")
  #   llmapsection_color_message.append([Color("red"), "no lo"])RE_DSMSCHED
  if last_color_schedulerc:
    section_color.add(last_color_schedulerc)
  return section_color, lmap_color_datetime_errorcode_msg_fndsmsched, lschedulerc, llmapsection_color_message



def format_it( nodename, ldsmc_query_fs, lmap_color_datetime_errorcode_msg_fndsmsched, lschedulerc, llmapsection_color_message):
    # lsection_message
    #
    # DSMC QUERY FS
    ret_dsmc_query_fs="DSMC QUERY FS :"+os.linesep+len("DSMC QUERY FS")*"-"+os.linesep
    if ldsmc_query_fs:
      llret=[]
      for dsmc_query_fs in ldsmc_query_fs:
        color, number, last_incr_datetime, last_incr_delta, fs_type, fs_name = dsmc_query_fs
        nice_last_incr_delta=":".join( last_incr_delta.__str__().split(":")[0:2])
        llret.append([color, nice_last_incr_delta, fs_name, fs_type, number])
    else:
      llret=[[Color("green"), "no entry"]]
    ret_dsmc_query_fs+=listlist2nicestr(llret)
    #
    # PARSE LOG
    llret=[]
    ret_log="PARSE LOG : (extracted from dsmcsched.log*)"+os.linesep+len("PARSE LOG")*"-"+os.linesep
    def datetime_sort_on_map_color_datetime_errorcode_msg_fndsmsched(a,b):
      return cmp(a[1], b[1])
    lmap_color_datetime_errorcode_msg_fndsmsched.sort(datetime_sort_on_map_color_datetime_errorcode_msg_fndsmsched)
    lmap_color_datetime_errorcode_msg_fndsmsched.reverse()
    if lmap_color_datetime_errorcode_msg_fndsmsched:
        for color, date_time, error_code, msg, fndsmsched in lmap_color_datetime_errorcode_msg_fndsmsched:
          if not error_code:
             error_code=""
          llret.append([color,"%s" % date_time.strftime("%Y-%m-%d %H:%M:%S"), error_code, msg])
    else:
      llret=[[Color("green"), "no entry"]]
    ret_log+=listlist2nicestr(llret)
    #
    # SCHEDULE RC 
    ret_schedulerc="SCHEDULE RC : (extracted from dsmcsched.log*)"+os.linesep+len("SCHEDULE RC")*"-"+os.linesep
    if llmapsection_color_message:
      ret_schedulerc+=listlist2nicestr(llmapsection_color_message)+2*os.linesep
    llret=[]
    for entry in lschedulerc:
      color, line=entry
      llret.append([color, line])
    ret_schedulerc+=listlist2nicestr(llret)
    #
    #
    ret="NODENAME: %s" % nodename + 2*os.linesep+ ret_dsmc_query_fs+2*os.linesep+ret_schedulerc+2*os.linesep+ret_log
    return ret

if '__main__' == __name__:
   parser = OptionParser()
   parser.add_option("--show-bb-cmd", action="store_true", dest="show_bb_cmd", default=False
                    ,help="this is used for debug purpose to see what actually is send to bb")
   (options, args) = parser.parse_args()
   page_color=Color("green")
   # dsmc_query_fs
   nodename, section_color_query_fs, ldsmc_query_fs=dsmc_query_filesystem()
   page_color.add(section_color_query_fs)
   # dsmc_sched_log
   section_color_log, lmap_color_datetime_errorcode_msg_fndsmsched, lschedulerc, lsection_message = read_dsmsched_log()
   page_color.add(section_color_log)
   # color
   if ( not is_launched_within_xymon() ) and (not options.show_bb_cmd) :
      TERMINAL_OR_WEB="terminal"
      data=format_it(nodename, ldsmc_query_fs, lmap_color_datetime_errorcode_msg_fndsmsched, lschedulerc, lsection_message)
      print(data)
      sys.exit(0)
   TERMINAL_OR_WEB="web"
   data=format_it(nodename, ldsmc_query_fs, lmap_color_datetime_errorcode_msg_fndsmsched, lschedulerc, lsection_message)
   lline_data=[]
   for line in data.split("\n"):
      lline_data.append(re.sub("^&(?P<color>\S+)\s+","&\g<color> ",line))
   data="\n".join(lline_data)
   data=data.replace(" ", "&nbsp;")
   cmd='%(bbcmd)s %(bbdisp)s "status+1h %(machine)s.%(testname)s %(display_color)s %(date)s \n%(data)s"' % \
       {'bbcmd':os.environ.get('BB','env_of_bb')
       ,'bbdisp':os.environ.get('BBDISP','env_of_bbdisp')
       ,'machine':os.environ.get('MACHINE','env_of_machine')
       ,'testname':HOBBIT_TESTNAME
       ,'date':NOW.strftime('%a, %d %b %Y %H:%M:%S h MET')
       ,'display_color':page_color.color
       ,'data':data
       }
   if ( options.show_bb_cmd )and( not is_launched_within_xymon() ):
      cmd.replace('\n', '\\\n')
      print(cmd)
      sys.exit(0)         
   if is_launched_within_xymon():
      os.system(cmd)
      sys.exit(0)
   parser.print_help()
   sys.exit(1)
