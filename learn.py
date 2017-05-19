import cv2, os, time, imutils
import argparse as ap
import numpy as np
import logging as log
from sklearn.svm import LinearSVC
from sklearn.externals import joblib
from scipy.cluster.vq import *
from sklearn.preprocessing import StandardScaler

start_time = time.time()

# Get the path of the training set
parser = ap.ArgumentParser()
parser.add_argument("-t", "--trainingSet", help="Path to Training Set", required="True")
parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
args = parser.parse_args()

if args.verbose:
    log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
    log.info("Verbose output.")
else:
    log.basicConfig(format="%(levelname)s: %(message)s")

# Get the training cllasses names and store them in a list
train_path = args.trainingSet
training_names = os.listdir(train_path)

# Get all the path to the images and save them in a list
# image_paths and the corresponding label in image_paths
image_paths = []
image_classes = []
class_id = 0

log.info("Carregando imagens")
#log.warning()
#log.error()

for training_name in training_names:
    dir = os.path.join(train_path, training_name) # Training directories
    class_path = imutils.imlist(dir)
    image_paths += class_path
    image_classes += [class_id]*len(class_path)
    class_id += 1

# Create feature extraction and keypoint detector objects

#fea_det = cv2.FeatureDetector_create("SIFT")
#des_ext = cv2.DescriptorExtractor_create("SIFT")

log.info("Extraindo caracteristicas")

sift = cv2.xfeatures2d.SIFT_create()

# List all descriptors stored

des_list = []

for image_path in image_paths:
    im = cv2.imread(image_path)
    #kpts = fea_det.detect(im)
    #kpts, des = des_ext.compute(im,kpts)
    (kpts, des) = sift.detectAndCompute(im, None)
    des_list.append((image_path,des))

descriptors = des_list[0][1]
for image_path, descriptor in des_list[1:]:
    descriptors = np.vstack((descriptors,descriptor))

log.info("Clusterizando caracteristicas")

#K-means
k = 100
voc, variance = kmeans(descriptors, k, 1)

im_features = np.zeros((len(image_paths), k), "float32")
for i in range(len(image_paths)):
    words, distance = vq(des_list[i][1], voc)
    for w in words:
        im_features[i][w] += 1

nbr_ocurrences = np.sum( (im_features > 0) * 1, axis = 0)
idf = np.array(np.log((1.0*len(image_paths)+1) / (1.0*nbr_ocurrences + 1)), 'float32')

stdSlr = StandardScaler().fit(im_features)
im_features = stdSlr.transform(im_features)

log.info("Treinando classificador")

clf = LinearSVC()
clf.fit(im_features, np.array(image_classes))

log.info("Salvando classificador")

joblib.dump((clf, training_names, stdSlr, k, voc), "bof.pkl", compress = 3)

log.info("--- %s seconds ---" % (time.time() - start_time))
