import argparse, cv2, imutils, os, time, numpy
from multiprocessing import Pool
from sklearn.svm import LinearSVC
from sklearn.externals import joblib
from sklearn.metrics import confusion_matrix
from scipy.cluster.vq import *

def get_args():
    # Get the path of the testing set
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-t", "--testingSet", help="Path to testing Set")
    group.add_argument("-i", "--image", help="Path to image")
    parser.add_argument("-c", "--classifierModelFile", help="Classifier Model File", required="True")
    parser.add_argument("-m", "--confusionMatrixName", help="Confusion Matrix Name", required="True")
    parser.add_argument('-v',"--visualize", action='store_true')
    return parser.parse_args()

def detectAndCompute(image_paths):
    des_list = []
    sift = cv2.xfeatures2d.SIFT_create()
    for image_path in image_paths:
        im = cv2.imread(image_path)
        (_, des) = sift.detectAndCompute(im, None)
        des_list.append((image_path,des))
    return des_list

def stack_descriptors(features):
    # Stack all the descriptors vertically in a numpy array
    #log.info("Stack all the descriptors vertically in a numpy array")
    descriptors = features[0].pop(0)[1]
    for feature in features:
        for _, descriptor in feature:
            descriptors = numpy.concatenate((descriptors, descriptor), axis=0)
    return descriptors

if __name__ == "__main__":
    start_time = time.time()

    args = get_args()

    # Load the classifier, class names, scaler, number of clusters and vocabulary
    clf, classes_names, stdSlr, k, voc = joblib.load(args.classifierModelFile + ".pkl")

    # Get the path of the testing image(s) and store them in a list
    print("Carregando imagens")
    image_paths = []
    if args.testingSet:
        test_path = args.testingSet
        try:
            testing_names = os.listdir(test_path)
        except OSError:
            print ("No such directory \(test_path)\nCheck if the file exists")
            exit()
        for testing_name in testing_names:
            dir = os.path.join(test_path, testing_name)
            class_path = imutils.imlist(dir)
            image_paths+=class_path
    else:
        image_paths = [args.image]

    # Create feature extraction and keypoint detector objects
    #fea_det = cv2.FeatureDetector_create("SIFT")
    #des_ext = cv2.DescriptorExtractor_create("SIFT")
    cpus = os.cpu_count()
    path_size = len(image_paths)
    path_lists_size = int(len(image_paths)/cpus)
    print("Dividing feature extraction between {} cpus".format(cpus))

    image_paths_parts = [image_paths[i:i + path_lists_size] for i in range(0, path_size, path_lists_size)]

    pool = Pool(processes=cpus)

    features = pool.map(detectAndCompute, (image_paths_parts))

    # Stack all the descriptors vertically in a numpy array
    descriptors = stack_descriptors(features)

    print("Criando codebook")
    test_features = numpy.zeros((len(image_paths), k), "float32")
    i = 0
    for feature in features:
        for image_path, descriptor in feature:
            words, _ = vq(descriptor, voc)
            for w in words:
                test_features[i][w] +=1
            i += 1

    # Perform Tf-Idf vectorization
    nbr_occurences = numpy.sum( (test_features > 0) * 1, axis = 0)
    idf = numpy.array(numpy.log((1.0*len(image_paths)+1) / (1.0*nbr_occurences + 1)), 'float32')

    # Scale the features
    test_features = stdSlr.transform(test_features)

    # Perform the predictions
    print("Realizando predições")
    predictions =  [classes_names[i] for i in clf.predict(test_features)]

    # Visualize the results, if "visualize" flag set to true by the user
    if args.visualize:
        for image_path, prediction in zip(image_paths, predictions):
            image = cv2.imread(image_path)
            cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
            pt = (0, 3 * image.shape[0] // 4)
            cv2.putText(image, prediction, pt ,cv2.FONT_HERSHEY_SCRIPT_COMPLEX, 2, [0, 255, 0], 2)
            cv2.imshow("Image", image)
            cv2.waitKey(3000)
    else:
        print("Calculando Acurácia...")
        total = 0
        hits = 0
        errors = 0
        for i in range(len(image_paths)):
            image_paths[i] = image_paths[i].split('/')[3]

        for classe, prediction in zip(image_paths, predictions):
            total += 1
            if prediction == classe:
                hits += 1
            else:
                errors += 1
        avg = (hits / total) * 100
        print("Total: {} - Acertos: {} - Erros: {} - Acuracia: {}".format(str(total),str(hits),str(errors), str(avg)))
        cnf_matrix = confusion_matrix(image_paths,predictions)
        #for i in len(cnf_matrix)
        print(cnf_matrix.shape)
        print(cnf_matrix)
        numpy.savetxt(args.confusionMatrixName + ".csv", cnf_matrix, delimiter=";", fmt="%10.f")
    print("--- %s seconds ---" % (time.time() - start_time))
