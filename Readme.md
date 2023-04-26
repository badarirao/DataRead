# DataRead
 DataRead is a gui software to visualize all the data generated from the ReRam software. 
 
 ## Software capabilities
  It first combines all the available files in the specified folder to an HDF5 file, and separates the metadata, and each loop data.
 Then, the user can load the generated HDF5 file into the software to visualize each of the data.
 
 The software tries to arrange the data according to the creation time as much as possible.
 
 ## User Guide
  First go to "File->Merge all data into H5" or press "ctrl+g" and select the folder where all the ReRam data exists. 
 This will convert all the data in the folder and subfolders into the required H5 format.
 Now click on "Add data" at the top right and select the desired .h5 file to be visualized.
 
 ## Tips
 - You can add multiple .h5 files into the list.
 - You can delete or reorder the data in the list and save the new list as a new .h5 file. 
   This is useful to remove unwanted data from your file, and create a new file with only important data.
 - You can change the x and y axis scales to linear or log, and you can also inverse the axis.
 - You can add additional details into the metadata section.
 - You can export the plots either individually or together as text, png, jpg, tiff or pdf files.
 
 ## Note
  It important to not change the file name of each file generated by the ReRam software, as this software identifies the nature of the file using the file name.
 For example, a file named sample_IV will be considered as an IV loop data, whereas sample_RV will be considered as an RV loop data. 
 Hence, even if you are changing the file name, leave the part after underscore intact.
 
 ## Software appearance
 ![DataRead_image](https://user-images.githubusercontent.com/47620203/234469083-62aff5cb-ccda-4f93-a958-ecdc46fef48c.jpg)

 
 