'''
This file is the main file that follows the paper "Multiple Nuclei 
Tracking Using Integer Programming for Quantitative Cancer Cell C-
ycle Analysis". The proposed algorithm mainly contains two parts: 
Nuclei Segmentation and Nuclei Tracking. 

Nuclei Segmentation:
It includes three steps:
1. Binarization - using adaptive thresholding - adaptivethresh.py
2. Nuclei center detection - using gradient vector feild (GVF) - gvf.py
3. Nuclei boundary delinating - using watershed algorithm - watershed.py

Nuclei Tracking:
It includes three steps:
1. Neighboring Graph Constrction
2. Optimal MatchingRAY
3. Cell Division, Death, Segmentation Errors Detection& Processing

'''
import cv2
import sys
import os
import numpy as np
import imageio
from adaptivethresh import ADPTIVETHRESH as athresh
from gvf import GVF
from matplotlib import pyplot as plt
from watershed import WATERSHED as WS
from graph_construction import GRAPH
from matching import FEAVECTOR as FEA
from matching import SIMPLE_MATCH as MAT
from PIL import Image

def normalize(image):
    '''
    This function is to normalize the input grayscale image by
    substracting globle mean and dividing standard diviation for
    visualization. 

    Input:  a grayscale image

    Output: normolized grascale image

    '''
    img = image.copy().astype(np.float32)
    img -= np.mean(img)
    img /= np.linalg.norm(img)
    # img = (img - img.min() )
    img = np.clip(img, 0, 255)
    img *= (1./float(img.max()))
    return (img*255).astype(np.uint8)

# read image sequence
# The training set locates at "resource/training/01" and "resource/training/02"
# The ground truth of training set locates at "resource/training/GT_01" and 
# "resource/training/GT_02"
# The testing set locates at "resource/testing/01" and "resource/testing/02"


path=os.path.join("/home/huoy1/Projects/celltracking/Fluo-N2DL-HeLa/01")
temp_path = os.path.join("/home/huoy1/Projects/celltracking/temporary_result_Hela")

for r,d,f in os.walk(path):
    images = []
    enhance_images = []
    f.sort()
    for files in f:
        if files[-3:].lower()=='tif':
            temp = cv2.imread(os.path.join(r,files))
            gray = cv2.cvtColor(temp, cv2.COLOR_BGR2GRAY) 
            images.append(gray.copy())
            enhance_images.append(normalize(gray.copy()))

print "Total number of image is ", len(images)
print "The shape of image is ", images[0].shape, type(images[0][0,0])

def write_image(image, title, index, imgformat='.tiff'):
    if index < 10:
            name = '0'+str(index)
    else:
        name = str(index)
    cv2.imwrite(title+name+imgformat, image)

def load_image(title, index, imgformat='.tiff'):
    if index < 10:
            name = '0'+str(index)
    else:
        name = str(index)
    img_file = title+name+imgformat
    if os.path.exists(img_file):
        img = cv2.imread(title+name+imgformat)
        return img
    else:
        return []

def main():

    # # Binarization
    th = athresh(enhance_images)
    threh = th.applythresh()
    write_image(threh[0]*255, "threh", 0)
    # Nuclei center detection
    gvf = GVF(images, threh)
    dismap = gvf.distancemap()
    newimg = gvf.new_image(4, dismap) # choose alpha as 0.4.
    write_image((dismap[0]*10).astype(np.uint8), "dismap", 0)
    write_image(newimg[0], "newimg", 0)
    gradimg = gvf.compute_gvf(newimg)

    temporary_result = os.path.join(temp_path)
    if not os.path.exists(temporary_result):
        os.makedirs(temporary_result)
    os.chdir(temporary_result)
    imgpairs = []
    # bin_imgpairs = []
    # imgpair_raws = []
    for i, grad in enumerate(gradimg):
        load_img = load_image('imgpair', i)
        if load_img == []:
            imgpair, bin_imgpair, imgpair_raw = gvf.find_certer(grad, i)
            imgpairs.append(imgpair)
            # bin_imgpairs.append(bin_imgpair)
            # imgpair_raws.append(imgpair_raw)
            # write_image(imgpair_raw, 'imgpair_raw', i)
            # write_image(bin_imgpair, 'bin_imgpair', i)
            write_image(imgpair, 'imgpair', i)
        else:
            imgpair = load_img
            imgpairs.append(imgpair)

    os.chdir(os.pardir)

    # watershed
    ws = WS(newimg, imgpairs)
    wsimage, binarymark, mark = ws.watershed_compute()

    centroid = []
    slope_length = []
    # Build Delaunay Triangulation
    for i in range(len(images)):
        graph = GRAPH(mark, binarymark, i)
        tempcentroid, tempslope_length = graph.run(False)
        centroid.append(tempcentroid)
        slope_length.append(tempslope_length)
        print('building Delaunay Triangulation %d/%d '%(i, len(images)))

    # Build the Dissimilarity measure vector
    vector = []
    for i in range(len(images)):
        print "  feature vector: image ", i
        v = FEA()
        v.set_centroid(centroid[i])
        v.set_spatial(slope_length[i])
        v.set_shape(enhance_images[i], mark[i])
        v.set_histogram()
        v.add_label()
        v.add_id(mark[i].max(), i)
        vector.append(v.generate_vector())

        print "num of nuclei: ", len(vector[i])

    # Feature matching
    mask = []

    for i in range(len(images)-1):
        print "  Feature matching: image ", i
        m = MAT(i,i+1,[images[i], images[i+1]], vector)
        mask.append(m.generate_mask(mark[i], i))
        m.find_match(0.3)
        mask = m.match_missing(mask, max_frame=2, max_distance=20)
        vector[i+1] = m.mitosis_refine()
        m.new_id()
        vector[i+1] = m.return_vectors()

    # write images if necessary
    # os.chdir(temporary_result)
    # for i in range(len(images)):
    #     # write_image(imgpair, 'imgpair', i)
    #     write_image(threh[i].astype(np.uint8)*255, 'threh', i)
    #     write_image(enhance_images[i], 'normalize', i)
    #     write_image(mark[i].astype(np.uint8), 'mark', i)
    #     write_image(binarymark[i].astype(np.uint8), 'binarymark', i)
    #     # write_image(tempimg[i].astype(np.uint8), 'tempimg', i)
    #     write_image(dismap[i].astype(np.uint8), 'dismap', i)
    # os.chdir(os.pardir)

    # write gif image showing the final result
    def find_max_id(temp_vector):
        max_id = 0
        for pv in temp_vector:
            for p in pv:
                if p.id > max_id:
                    max_id = p.id
        return max_id

    # This part is to mark the result in the normolized image and
    # write the gif image.
    max_id = find_max_id(vector)
    max_id = int(max_id)
    colors = [np.random.randint(0, 255, size=max_id), \
              np.random.randint(0, 255, size=max_id), \
              np.random.randint(0, 255, size=max_id)]
    font = cv2.FONT_HERSHEY_SIMPLEX
    selecy_id = 9
    enhance_imgs = []
    for i, m in enumerate(mask):
        print "  write the gif image: image ", i
        enhance_imgs.append(cv2.cvtColor(enhance_images[i], cv2.COLOR_GRAY2RGB))
        for pv in vector[i]:
            center = pv.c
            if not pv.l:
                color = (colors[0][int(pv.id) - 1], \
                         colors[1][int(pv.id) - 1], \
                         colors[2][int(pv.id) - 1],)
            else:
                color = (colors[0][int(pv.l) - 1], \
                         colors[1][int(pv.l) - 1], \
                         colors[2][int(pv.l) - 1],)

            if m[int(center[0]), int(center[1])]:
                enhance_imgs[i][m == pv.id] = color
                cv2.putText(enhance_imgs[i], \
                            str(int(pv.id)), (int(pv.c[1]), \
                                              int(pv.c[0])),
                            font, 0.5, \
                            (255, 255, 255), 1)
    os.chdir(temporary_result)
    imageio.mimsave('mitosis_final.gif', enhance_imgs, duration=0.6)
    print "finish!"

# if python says run, then we should run
if __name__ == '__main__':
    main()