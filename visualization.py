
import numpy as np
import pickle
import matplotlib.pyplot as plt
import hnswlib
import itertools
from scipy.io import savemat, loadmat
import cv2
import glob


# load vlad files
vlads_file = "vladFiles/NewCollegeVLADs.pickle"

with open(vlads_file, 'rb') as f:
    VLADs = pickle.load(f)


# load GT matrix
groundtruthPath = 'datasets/NewCollege/NewCollegeGroundTruth.mat'
groundtruthMat = loadmat(groundtruthPath)
groundtruthMat

# extract right view
groundtruthMat = groundtruthMat['truth'][::2, ::2]
groundtruthMat

gt_loop = np.count_nonzero(np.sum(groundtruthMat, 1))


dim = 10 * len(VLADs[0])
num_elements = len(VLADs)

p = hnswlib.Index(space='l2', dim=dim)

p.init_index(max_elements=num_elements, ef_construction=100, M=64)
p.set_ef(100)


image_num = len(VLADs)
matches = np.nan * np.ones([image_num, 2])

for index, vlad in enumerate(VLADs):
    print('index: ', index)

    # construction start from index=19
    if index >= 19:

        # add node 10 frames earlier
        vlad_seq_add = VLADs[index-19:index-9]
        node_add = np.array(
            list(itertools.chain.from_iterable(vlad_seq_add)), dtype='float32')
        p.add_items(node_add, index-10)

        # detection start from index=100
        if index >= 100:

            vlad_seq = VLADs[index-9:index+1]
            node = np.array(
                list(itertools.chain.from_iterable(vlad_seq)), dtype='float32')

            # 给定 query，返回搜索结果
            # 返回的 indices 和 distances 都是 np.array
            indice, distance = p.knn_query(node, k=1)

            matches[index, 0] = int(indice)
            matches[index, 1] = int(distance)


matches[:, 1] = matches[:, 1] / np.nanmax(matches[:, 1])

# Evaluation the matches by PR curve

pr = []
row = matches.shape[0]

for mu in np.arange(0, 1, 0.01):
    idx = np.copy(matches[:, 0])  # The LARGER the score, the WEAKER the match.
    idx[matches[:, 1] > mu] = np.nan  # remove the weakest matches

    loopMat = np.zeros((row, row))
    for i in range(row):
        if not np.isnan(idx[i]):
            loopMat[i, int(idx[i])] = 1

    p_loop = np.sum(loopMat)
    TP = np.sum(loopMat * groundtruthMat)
    if p_loop != 0:
        pre = TP / p_loop
        rec = TP / gt_loop
        print("mu: ", mu, "pre: ", pre, " rec: ", rec)
        pr.append([pre, rec])


pr = np.array(pr)

# plt.subplots() is recommended by matplotlib
fig, ax = plt.subplots()
ax.plot(pr[:, 1], pr[:, 0], '-o')
print(len(pr))
ax.set_title('PR Curve')
ax.set_xlabel('Recall')
ax.set_ylabel('Precision')
ax.grid()
plt.axis([0, 1.05, 0, 1.05])
plt.show()




# show matched images, correct or not
mu = 0.9

idx = np.copy(matches[:, 0])  # The LARGER the score, the WEAKER the match.
idx[matches[:, 1] > mu] = np.nan  # remove the weakest matches
loopMat = np.zeros((row, row))

for i in range(row):
     if not np.isnan(idx[i]):
         loopMat[i, int(idx[i])] = 1

path = 'datasets/NewCollege/Images'   
imagePaths = sorted(glob.glob(path+"/*.jpg"))[::2]

for i in range(row):
    for j in range(row):
        if loopMat[i,j] == 1 and groundtruthMat[i,j] == 1:
            img1 = cv2.imread(imagePaths[i])
            img2 = cv2.imread(imagePaths[j])
            cv2.imshow("Correct match 1", img1)
            cv2.imshow("Correct match 2", img2)
            cv2.waitKey()
        elif loopMat[i,j] == 1 and groundtruthMat[i,j] == 0:
            img1 = cv2.imread(imagePaths[i])
            img2 = cv2.imread(imagePaths[j])
            cv2.imshow("Incorrect match 1", img1)
            cv2.imshow("Incorrect match 2", img2)
            cv2.waitKey()



# show conffusion matrix as an image
confImg = np.zeros((row, row, 3), np.uint8)
for i in range(row):
    for j in range(row):
        if groundtruthMat[i,j] == 1:
            if loopMat[i,j] == 0:
                confImg[i,j,:] = (255,255,255)
            else:
                cv2.circle(confImg, (j,i), 3, (0,0,255), -1) 

cv2.namedWindow("Confusion matrix", cv2.WINDOW_NORMAL)
cv2.imshow("Confusion matrix", confImg)
cv2.resizeWindow("Confusion matrix", 800,800)
cv2.waitKey()

cv2.imwrite("confImage.jpg", confImg)