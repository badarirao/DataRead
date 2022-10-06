
import glob
import os
import numpy as np
from datetime import datetime
import pandas as pd
from tables import exceptions
import re

#TODO check if removing unicode characters from filename affects hdf5 file losing any stored data, due to same experiment name.
def h5store(filename, df, keyName, mode, **kwargs):
    store = pd.HDFStore(filename, mode=mode)
    store.put(keyName, df)
    store.get_storer(keyName).attrs.metadata = kwargs
    store.close()


def get_Measurement_list(folderPath):
    """
    Scans a folder for experimental data, sorts it according to last modified time, 
    and separates into different experiment groups after analyzing the file names.

    Parameters
    ----------
    folderPath : string
        The path of the folder to scan.

    Returns
    -------
    list_of_experiments : list
        list of all experiments sorted into their respective experiment groups, and modified time
    experiment_names : list
        names of experiment groups
    """
    # modify the delimiter in RV and switch file to tab. Some old files have , as the delimiter.
    # Also, if switch file is saved as .csv, change it to .dat (some old files are as .csv)
    allFileList = list(filter(os.path.isfile, glob.glob(folderPath + '\\*.*')))
    allFile_mtime = [os.path.getmtime(file) for file in allFileList]
    for i,file in enumerate(allFileList):
        if '_Switch' in file or '_RV' in file or '_Retention' in file:
            if file.endswith('.csv'):
                os.rename(file, file[:-4] + '.dat')
                file = file[:-4] + '.dat'
            with open(file, 'r') as f:
                lines = f.readlines()
                newlines = []
                for line in lines:
                    if '#' not in line and ',' in line:
                        line = line.replace(',','\t')
                    newlines.append(line)
            with open(file, 'w') as f:
                f.writelines(newlines)
            os.utime(file,(allFile_mtime[i],allFile_mtime[i]))
    list_of_filePaths = list(
        filter(os.path.isfile, glob.glob(folderPath + '\\*.dat')))
    list_of_filePaths.sort(key=os.path.getctime)
    list_of_files = [file.split('\\')[-1][:-4] for file in list_of_filePaths]
    experiment_names = []
    for filePath in list_of_files:
        file = filePath.split('\\')[-1]
        if '_IV' in file:
            index = file.rindex('_IV')
        elif '_RV' in file:
            index = file.rindex('_RV')
        elif '_Switch' in file:
            index = file.rindex('_Switch')
        elif '_Fatigue' in file:
            index = file.rindex('_Fatigue')
        elif '_Retention' in file:
            index = file.rindex('_Retention')
        elif '_Forming' in file:
            index = file.rindex('_Forming')
        else:
            index = -4
        #file = re.sub(regex,'',file[:index])
        file = file[:index]
        experiment_names.append(file)
    experiment_names = list(dict.fromkeys(experiment_names))
    n_experiments = len(experiment_names)
    list_of_experiments = [[] for i in range(n_experiments)]
    for i, name in enumerate(experiment_names):
        j = 0
        while True:
            if '_IV' in list_of_files[j]:
                index = list_of_files[j].rindex('_IV')
            elif '_RV' in list_of_files[j]:
                index = list_of_files[j].rindex('_RV')
            elif '_Switch' in list_of_files[j]:
                index = list_of_files[j].rindex('_Switch')
            elif '_Fatigue' in list_of_files[j]:
                index = list_of_files[j].rindex('_Fatigue')
            elif '_Retention' in list_of_files[j]:
                index = list_of_files[j].rindex('_Retention')
            elif '_Forming' in list_of_files[j]:
                index = list_of_files[j].rindex('_Forming')
            else:
                index = -4
            exptName = list_of_files[j][:index]
            if name == exptName:
                list_of_experiments[i].append(list_of_filePaths.pop(j))
                list_of_files.pop(j)
            else:
                j += 1
            if j >= len(list_of_files):
                break
    
    return list_of_experiments, experiment_names

def extract_metadata(comments):
    general_comment = []
    metadata = {}
    for comment in comments:
        if ':' in comment:
            metD = comment.split(':')
            if len(metD) == 2:
                if metD[1] != '':
                    metadata[metD[0].replace('#','').strip()] = metD[1].strip().replace(' ',' ,')
                else:
                    general_comment.append(":".join(metD))
            else:
                general_comment.append(":".join(metD))
        elif ',' in comment:
            cparts = comment.split(',')
            for c in cparts:
                if '=' in c:
                    metD = c.split('=')
                    if len(metD) == 2:
                        metadata[metD[0].replace(
                            '#', '').strip()] = metD[1].strip()
                    else:
                        general_comment.extend("=".join(metD))
                else:
                    general_comment.append(c)
        elif '=' in comment:
            metD = comment.split('=')
            if len(metD) == 2:
                metadata[metD[0].replace('#', '').strip()] = metD[1].strip()
            else:
                general_comment.extend("=".join(metD))
        else:
            general_comment.append(comment)
    metadata["Comments"] = '\n'.join(general_comment)
    return metadata
    
def load_general_file(file):
    """
    load the measurement file like switch, forming, retention, fatigue
    :param file:
    :return: metadata, headers and data
    """
    comments = []
    formingData = []
    with open(file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            elif '#' in line:
                if '\t' in line:
                    headers = line.replace("#",'').strip().split('\t')
                else:
                    comments.append(line.replace("#",''))
            elif 'voltage' in line.lower() or 'current' in line.lower():
                headers = line.replace("#",'').strip().split('\t')
            elif not line[:1].isdigit() and line[:1] != '-' and line[:1] != '+':
                headers = line.replace("#",'').strip().split('\t')
            else:
                try:
                    data_point = [float(x) for x in line.split('\t')]
                    formingData.append(np.array(data_point))
                except:
                    print(f"Error in {file}")
        formingData = np.array(formingData)
        if headers:
            headers = [h.strip() for h in headers]
        if "_Switch" in file:
            try:
                indexRV = headers.index("Read Voltage (V)")
                uniqueRVs = ', '.join(map(str,np.unique(formingData[:,indexRV])))
                comments.append(f"Read voltage used (V): {uniqueRVs}")
            except:
                pass
            try:
                indexPW = headers.index("Pulse Width (ms)")
                uniquePWs = ', '.join(map(str,np.round(np.unique(formingData[:,indexPW])*1000,3)))
                comments.append(f"Pulse width used (ms): {uniquePWs}")
            except:
                pass
            try:
                indexCC = headers.index("Compliance current (A)")
                uniqueCCs = ', '.join(map(str,np.unique(formingData[:,indexCC])*1000))
                comments.append(f"Compliance current set (mA): {uniqueCCs}")
            except:
                pass
            try:
                indexV = headers.index("Pulse Voltage (V)")
                uniqueVs = ', '.join(map(str,np.unique(formingData[:,indexV])))
                comments.append(f"Set Pulse voltage (V): {uniqueVs}")
            except:
                pass

    return extract_metadata(comments), headers, formingData                

def load_IV_file(file):
    """
    load the IV loop data from file
    :param file:
    :return: data, headers and metadata
    """
    comments = []
    allLoopsData = []
    oneLoopData = []
    finishedOneCycle = False
    with open(file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line[:2] == '##':
                comments.append(line[2:].strip())
            elif 'Cycle' in line:
                if finishedOneCycle:
                    allLoopsData.append(np.array(oneLoopData))
                    oneLoopData = []
                    finishedOneCycle = False
            elif not line:
                finishedOneCycle = True
            elif 'voltage' in line.lower() or 'current' in line.lower():
                headers = line.replace('#', '').split('\t')
            else:
                data_point = [float(x) for x in line.split('\t')]
                oneLoopData.append(data_point)
        if oneLoopData:
            allLoopsData.append(np.array(oneLoopData))
    return extract_metadata(comments), headers, allLoopsData

def load_RV_file(file):
    """
    Parameters
    ----------
    file : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.
    headers : TYPE
        DESCRIPTION.
    allLoopsData : TYPE
        DESCRIPTION.

    """
    comments = []
    allLoopsData = []
    oneLoopData = []
    headers = []
    finishedOneCycle = False
    with open(file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith('##'):
                comments.append(line[2:].strip())
            elif 'Cycle' in line:
                if finishedOneCycle:
                    allLoopsData.append(np.array(oneLoopData))
                    oneLoopData = []
                    finishedOneCycle = False
            elif 'voltage' in line.lower() or 'current' in line.lower():
                headers = line.replace('#', '').split('\t')
            elif not line:
                finishedOneCycle = True
            else:
                data_point = [float(x) for x in line.split('\t')]
                oneLoopData.append(data_point)
        if oneLoopData:
            allLoopsData.append(np.array(oneLoopData))
    return extract_metadata(comments), headers, allLoopsData

def create_hdf_file(experimentName, experimentList):
    """
    Read a single experiment file and load data, metadata and store it into a single hdf5 file.

    Parameters
    ----------
    file : string
        file name of the experiment data.

    Returns
    -------
    None.

    """
    mode = 'w'
    regex = r'[^A-Za-z0-9_:./\-\\]'
    # if you want to append new data into existing file, set mode to append.
    # else overwrite the data into a fresh file.
    # It is okay to check only the first file, because experimentList contains oldest file first.
    file = experimentList[0]
    pathname = file.replace(file.split('\\')[-1],'')
    if os.path.isfile(pathname+experimentName+'.h5'):
        store = pd.HDFStore(pathname+experimentName+'.h5')
        fnames = store.keys()
        for f in fnames:
            if file == f.split('/')[1]:
                mode = 'a'
                break
    else:
        mode = 'a'
    if mode == 'w':
        store.close()
    for file in experimentList:
        created_time = os.path.getctime(file)
        modified_time = os.path.getmtime(file)
        if modified_time < created_time:
            created_time = modified_time
        general_metadata = {"timestamp" : datetime.fromtimestamp(created_time),
                            "File Name" : file[:-4].split('\\')[-1]}
        fileName = file[:-4].split('\\')[-1]  # remove .dat from filename
        fileName = re.sub(regex, '', fileName)
        experimentName = re.sub(regex,'',experimentName)
        if '_IV' in file:
            general_metadata["measurement"] = "IV"
            metadata, headers, ivloops = load_IV_file(file)
            metadata["Actual cycles measured"] = len(ivloops)
            metadata = {**general_metadata, **metadata} # merge the two metadatas
            loopNo = 1
            for loop in ivloops:
                if len(ivloops) > 1:
                    keyName = fileName + '/loop_' + str(loopNo)
                else:
                    keyName = fileName
                metadata["Loop number"] = loopNo
                try:
                    df = pd.DataFrame(data=loop, columns=headers)
                except ValueError:
                    print(headers)
                h5store(pathname+experimentName+'.h5', df, keyName, mode, **metadata)
                loopNo += 1
        elif '_RV' in file:
            general_metadata["measurement"] = "RV"
            metadata, headers, rvloops = load_RV_file(file)
            metadata["Actual cycles measured"] = len(rvloops)
            metadata = {**general_metadata, **metadata} # merge the two metadatas
            loopNo = 1
            for loop in rvloops:
                if len(rvloops) > 1:
                    keyName = fileName + '/loop_' + str(loopNo)
                else:
                    keyName = fileName
                metadata["Loop number"] = loopNo
                df = pd.DataFrame(data=loop, columns=headers)
                h5store(pathname+experimentName+'.h5', df, keyName, mode, **metadata)
                loopNo += 1
        else:
            if '_Switch' in file:
                general_metadata["measurement"] = "Switch"
            elif '_Fatigue' in file:
                general_metadata["measurement"] = "Fatigue"
            elif '_Retention' in file:
                general_metadata["measurement"] = "Retention"
            elif '_Forming' in file:
                general_metadata["measurement"] = "Forming"
            metadata, headers, measureData = load_general_file(file)
            metadata = {**general_metadata, **metadata} # merge the two metadatas
            df = pd.DataFrame(data=measureData, columns=headers)
            h5store(pathname+experimentName+'.h5', df, fileName, mode, **metadata)
        mode = 'a'

if __name__ == "__main__":
    # delete any preexisting hdf file before running this program
    # It will not rewrite the hdf file, but will append the file
    path = "D:\AFO6006"
    pathname = os.path.normpath(path)

    for root, dirs, files in os.walk(pathname):
        list_of_experiments, experiment_names = get_Measurement_list(root)
        if experiment_names:
            for i in range(len(experiment_names)):
                try:
                    create_hdf_file(experiment_names[i],list_of_experiments[i])
                except exceptions.HDF5ExtError as e:
                    print(e)
                    print("Got HDF5 Error for {}".format(experiment_names[i]))
                    print('most likely, there is some problem with the folder name. Please correct it')
                    pass
    
