'''
Created on Oct 22, 2013

@author: nicodjimenez

This file will save a dictionary mapping from symbols to lists of examples.
This dictionary is saved to a pickle file for easier access.

TODO: cubic interpolation fcn
'''

import cv2
from scipy.interpolate import interp1d
import glob
import os 
import cPickle as pickle
import xml.etree.ElementTree as ET
# used for debugging only
from xml.etree.ElementTree import dump as xml_dump
import numpy as np
from StringIO import StringIO
from pylab import *
from skimage import morphology

# are we plotting all the image transformations
DEBUG = False

# pixel dimensions to which we are going to downsample
PIXEL_DIM = 28

# pixel resolution at the point we do segmentation 
SEG_DIM = 100.0

# are we going to plot all the symbmols as they come along? (just for debugging)
PLOT_ME = False

# where is the data relative to current directory
REL_PATH = "../data/CROHME2012_data/trainData"

# where are we saving the outputs to
DUMP_LOCATION = "../pickle_files/"
SAVE_FILENAME = os.path.join(DUMP_LOCATION,"raw_symbols.p")

# x resolution which will be used to interpolate between data points
INTERP_RES = 1

def xy_to_cv(data_arr):
    """
    Converts xy pairs to a openCV formatted matrix.
    """
    max_x = max(data_arr[:,0])
    max_y = max(data_arr[:,1])
    max_xy = max([max_x,max_y])
    dim_stretch = SEG_DIM / max_xy
    data_arr = data_arr * dim_stretch
    
    vis = 255 * np.ones((SEG_DIM+1, SEG_DIM+1),np.uint8)
    
    # place all values in binary image
    for elem in data_arr: 
        vis[SEG_DIM - int(elem[1]) ,int(elem[0])] = 0
        
    return vis

def gen_opencv_mat(data_arr):
    """
    Some experimentation with segmenting symbols.
    """
    bin_mat = xy_to_cv(data_arr)
    
    vis_2 = cv2.cvtColor(bin_mat,cv2.COLOR_GRAY2BGR)
    cv2.imwrite('sof2.png',vis_2)
        
    # Load the image
    img = cv2.imread('sof2.png')
    #img = cv2.imread('test_case.png')
    
    # convert to grayscale
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    
    # smooth the image to avoid noises
    gray = cv2.medianBlur(gray,0)
    
    if DEBUG:
        cv2.imshow('gray_img',gray)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    
    # Apply adaptive threshold
    thresh = cv2.adaptiveThreshold(gray,255,1,1,11,2)
    
    if DEBUG:
        cv2.imshow('thresh',thresh)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    
    thresh_color = cv2.cvtColor(thresh,cv2.COLOR_GRAY2BGR)
    # apply some dilation and erosion to join the gaps
    thresh = cv2.dilate(thresh,None,iterations = 1)
    
    if DEBUG:
        cv2.imshow('thresh_after_dilation',thresh)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
#     thresh = cv2.erode(thresh,None,iterations = 1)
#         
#     if DEBUG:
#         cv2.imshow('thresh_after_erode',thresh)
#         cv2.waitKey(0)
#         cv2.destroyAllWindows()
    
    # Find the contours
    contours,hierarchy = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    
    # For each contour, find the bounding rectangle and draw it
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.rectangle(thresh_color,(x,y),(x+w,y+h),(0,255,0),2)
    
    if DEBUG:
        # Finally show the image
        cv2.imshow('img',img)
        cv2.imshow('res',thresh_color)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
#     
#     label_number = 0
#     
#     for label_number in range(np.max(labels)):
#         temp = np.uint8(labels==label_number) * 255
#         if not cv2.countNonZero(temp):
#             break
#         cv2.imshow('result', temp), cv2.waitKey(0)

    return None

def normalize_symbol(data_arr):
    """
    Takes symbols and aligns them at the bottom left corner. 
    """
    
    # must flip this dimension (it's f-ed up in the inkml files)
    data_arr[:,1] = -1 * data_arr[:,1]
    min_x = min(data_arr[:,0]) - 200
    min_y = min(data_arr[:,1]) - 200
    
    sub_vec = np.array([min_x,min_y])
    
    for (ind,elem) in enumerate(data_arr): 
        data_arr[ind] = elem - sub_vec
        
    return data_arr

def lin_interp_stroke(data_arr):
    """
    Takes stroke array as input and returns linearly interpolated
    stroke array. 
    """
    
    KIND = 'linear'
    interp_data_arr = None
    data_len = len(data_arr)
    
    for ind in range(data_len-1):  
        
        #print data_arr[ind:ind+2,:]
        x_diff = abs(data_arr[ind,0] - data_arr[ind+1,0])
        y_diff = abs(data_arr[ind,1] - data_arr[ind+1,1])
        
        if x_diff > y_diff: 
            if data_arr[ind,0] < data_arr[ind+1,0]:
                g = interp1d([data_arr[ind,0],data_arr[ind+1,0]] ,[data_arr[ind,1],data_arr[ind+1,1]],kind=KIND)
            else:
                g = interp1d([data_arr[ind+1,0],data_arr[ind,0]] ,[data_arr[ind+1,1],data_arr[ind,1]],kind=KIND)
                     
            #g = interp1d(data_arr[ind:ind+2,0], data_arr[ind:ind+2,1])
            
            x_new = np.arange(min(data_arr[ind:ind+2,0]),max(data_arr[ind:ind+2,0]),INTERP_RES)
            y_new = g(x_new)
        else: 
            if data_arr[ind,1] < data_arr[ind+1,1]:
                g = interp1d([data_arr[ind,1],data_arr[ind+1,1]] ,[data_arr[ind,0],data_arr[ind+1,0]],kind=KIND)
            else:
                g = interp1d([data_arr[ind+1,1],data_arr[ind,1]] ,[data_arr[ind+1,0],data_arr[ind,0]],kind=KIND)
                     
            #g = interp1d(data_arr[ind:ind+2,0], data_arr[ind:ind+2,1])
            
            y_new = np.arange(min(data_arr[ind:ind+2,1]),max(data_arr[ind:ind+2,1]),INTERP_RES)
            x_new = g(y_new)
            
        
        new_data_arr = np.vstack((x_new,y_new)).T
        
        if interp_data_arr == None: 
            interp_data_arr = new_data_arr
        else:
            interp_data_arr = np.vstack((interp_data_arr,new_data_arr))
            
    return interp_data_arr
    
def remove_outliers(data_arr):
    """
    Takes array as input and deletes garbage indices.
    """
    ind_delete = []
    for (ind,val) in enumerate(data_arr[:,1]):
        if abs(val) > 1E6:
            ind_delete.append(ind)
    
    data_arr = np.delete(data_arr, ind_delete,0)
    
    return data_arr

def stroke_to_arr(stroke):
    """
    Takes in stroke text and returns stroke array.
    """
    
    stroke = stroke.replace(',', '\n')
    stroke_IO = StringIO(stroke)
    stroke_arr = np.loadtxt(stroke_IO)
    #stroke_arr[1,:] = -1 * stroke_arr[1,:]
    
    return stroke_arr
    
def loop_over_data():
    # get the list of .inkml files
    xml_file_list = glob.glob(os.path.join(REL_PATH,"*.inkml"))
    symbol_dict = {}
    ct = 0
    
    for cur_file in xml_file_list:
        tree = ET.parse(cur_file)
        root = tree.getroot()
        
        # gather list of all strokes
        full_trace_list = root.findall("{http://www.w3.org/2003/InkML}trace")
        
        # this is a group of a group of strokes which make up the whole expression
        traceGroup_parent = root.find("{http://www.w3.org/2003/InkML}traceGroup")
        
        # for each subgroup of strokes in the expression corresponding to a symbol
        for traceGroup in traceGroup_parent: 
            
            # look for the annotation of the current group of strokes which will contain
            # the truth value of the stroke
            part = traceGroup.find("{http://www.w3.org/2003/InkML}annotation")
            
            if part == None:
                continue
            
            ct += 1
            symbol = part.text
            
            # get the indices of the single strokes which comprise the current symbol
            cur_trace_list = traceGroup.findall("{http://www.w3.org/2003/InkML}traceView")
            trace_id_list = [int(elem.attrib.get('traceDataRef')) for elem in cur_trace_list]
            
            # now we build a string with comma separated fields that will contain all the 
            # positions of the sybmol, aggregated from all the constituent stokes
            new_cur_data = None
            
            for trace_id in trace_id_list:
                stroke = full_trace_list[trace_id].text
                stroke_arr = stroke_to_arr(stroke)
                stroke_arr = lin_interp_stroke(stroke_arr) 
                
                if new_cur_data == None:
                    new_cur_data = stroke_arr
                else: 
                    new_cur_data = np.vstack((new_cur_data,stroke_arr))
                    
            new_cur_data = normalize_symbol(new_cur_data)
            gen_opencv_mat(new_cur_data)
            
            if PLOT_ME: 
                scatter(new_cur_data[:,0],new_cur_data[:,1])
                #xlim([0,20000])
                #ylim([10000,0])
                title(symbol)
                show()
            
            if symbol in symbol_dict:
                symbol_dict[symbol].append(new_cur_data)
            else:
                symbol_dict.update({symbol:[new_cur_data]})
    
    with open(SAVE_FILENAME,'wb') as f:
        pickle.dump(symbol_dict, f, protocol=0)   
        
    print "Successfully saved pickle file to: " + str(SAVE_FILENAME)
    
if __name__ == "__main__":
    loop_over_data()
    
#for symbol in symbol_dict:
#    print symbol, len(symbol_dict[symbol])
#print "Total number of example characters: ", ct



    

