#!/bin/python
#title           :fork_clones.py
#description     :Creating a DevOps like on Solaris
#author          :Eli Kleinman
#date            :20181018
#version         :0.1
#usage           :python fork_clones.py
#notes           :
#python_version  :2.7.14 

import multiprocessing 
import subprocess
import os, sys

if len(sys.argv) == 1:
   print('Usage: Number of workloads!')
   sys.exit()

numJobs = int(sys.argv[1])

def worker(num):
    proc = num+301
    jirid = 'jir'+str(proc)
    print("%s Started!" % (jirid))
    p = subprocess.Popen(['/var/tmp/elik/informix_project/clone_zfs.py', '-i', jirid], stdout=subprocess.PIPE)
    #p = subprocess.Popen(['/var/tmp/elik/informix_project/clone_zfs.py', '-d','-i', jirid], stdout=subprocess.PIPE)
    out, err = p.communicate()
    print out
    print("%s Completed!" % (jirid))
    return

if __name__ == '__main__':
    jobs = []
    for i in range(numJobs):
        p = multiprocessing.Process(target=worker, args=(i,))
        jobs.append(p)
        p.start()
