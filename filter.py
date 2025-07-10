# Tutorial https://learnopencv.com/create-snapchat-instagram-filters-using-mediapipe/
# Filter image from https://lovepik.com/image-401708795/green-peking-opera-facebook.html
import cv2
import mediapipe as mp
import numpy as np
import csv
import faceBlendCommon as fbc
import math
# import time
# from concurrent.futures import ThreadPoolExecutor

VISUALIZE_FACE_POINTS = False

filters_config = {
    'jing':
        [{'path': "filters/jing.png",
         'anno_path': "filters/labels_jing_new.csv",
         'morph': True, 'animated': False, 'has_alpha': True}]
}


# It can also work with using landmark_pb2 mddoel from the mediapipe framework, but it's also work with mediapipe solutions
# The mp_face_landmarker.py shows that I know how to use the mediapipe framework
def get_landmarks_from_mesh(image):
    mp_face_mesh = mp.solutions.face_mesh
    # pre-selected landmark indices for the filter
    selected_landmarks = [127, 93, 58, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 288, 323, 356, 70, 63, 105, 66, 55,
                 285, 296, 334, 293, 300, 168, 6, 195, 4, 64, 60, 94, 290, 439, 33, 160, 158, 173, 153, 144, 398, 385,
                 387, 466, 373, 380, 61, 40, 39, 0, 269, 270, 291, 321, 405, 17, 181, 91, 78, 81, 13, 311, 306, 402, 14,
                 178, 162, 54, 67, 10, 297, 284, 389]
 
    height, width = image.shape[:-1]
    with mp_face_mesh.FaceMesh(max_num_faces=1, static_image_mode=True, min_detection_confidence=0.5) as face_mesh:
 
        results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
 
        if not results.multi_face_landmarks:
            print("No face detected.")
            return 
 
        for face_landmarks in results.multi_face_landmarks:
            values = np.array(face_landmarks.landmark)
            face_coordinates = np.zeros((len(values), 2))
 
            # Extract the x, y coordinates of the face landmarks
            for idx,value in enumerate(values):
                face_coordinates[idx][0] = value.x
                face_coordinates[idx][1] = value.y
 
            # Convert normalized points to image coordinates
            face_coordinates = face_coordinates * (width, height)
            face_coordinates = face_coordinates.astype("int")
 
            relevant_coordinates = []
 
            for i in selected_landmarks:
                relevant_coordinates.append(face_coordinates[i])
            return relevant_coordinates
    return 

def load_filter_image(image_path, has_alpha):
    # Read the image
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
 
    alpha = None
    if has_alpha:
        b, g, r, alpha = cv2.split(image)
        image = cv2.merge((b, g, r))
 
    return image, alpha

def load_landmarks(annotation_file):
    with open(annotation_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        points = {}
        for i, row in enumerate(csv_reader):
            # skip head or empty line if it's there
            try:
                x, y = int(row[1]), int(row[2])
                points[row[0]] = (x, y)
            except ValueError:
                continue
        return points

# Instead of find the contours, like using gradiants, we can use the convex hull to find the face shape
def find_convex_hull(points):
    hull = []
    # The index points of the face filter which will be mapped to the face landmarks
    hullIndex = cv2.convexHull(np.array(list(points.values())), clockwise=False, returnPoints=False)
    addPoints = [
        [48], [49], [50], [51], [52], [53], [54], [55], [56], [57], [58], [59],  # Outer lips
        [60], [61], [62], [63], [64], [65], [66], [67],  # Inner lips
        [27], [28], [29], [30], [31], [32], [33], [34], [35],  # Nose
        [36], [37], [38], [39], [40], [41], [42], [43], [44], [45], [46], [47],  # Eyes
        [17], [18], [19], [20], [21], [22], [23], [24], [25], [26]  # Eyebrows
    ]
    # print(len(hullIndex))
    hullIndex = np.concatenate((hullIndex, addPoints))
    for i in range(0, len(hullIndex)):
        # print(i," ",points[str(hullIndex[i][0])])
        hull.append(points[str(hullIndex[i][0])])
 
    return hull, hullIndex

# The function to load the only filter that I have
def load_filter(filter_name="jing"):
    filters = filters_config[filter_name] 
    multi_filter_runtime = [] 
    for filter in filters:
        dict = {}
 
        image1, image1_alpha = load_filter_image(filter['path'], filter['has_alpha'])
 
        dict['image'] = image1
        dict['image_a'] = image1_alpha
 
        points = load_landmarks(filter['anno_path'])
 
        dict['points'] = points

        # call dlib library and fbc module to find the convex hull and delaunay triangulation
        if filter['morph']:
            hull, hullIndex = find_convex_hull(points)
            sizeimage1 = image1.shape
            rect = (0, 0, sizeimage1[1], sizeimage1[0])
            dt = fbc.calculateDelaunayTriangles(rect, hull)
 
            dict['hull'] = hull
            dict['hullIndex'] = hullIndex
            dict['dt'] = dt
 
            if len(dt) == 0:
                continue
 
        # it is not avaliable in this moment
        if filter['animated']:
            filter_cap = cv2.VideoCapture(filter['path'])
            dict['cap'] = filter_cap
 
        multi_filter_runtime.append(dict)
 
    return filters, multi_filter_runtime

def main():
    # Input from webcam
    cap = cv2.VideoCapture(0)
    
    # Some global(?) variables
    count = 0
    isFirstFrame = True
    sigma = 50
    
    # Load an initial filter, I don't have more filter so it's just decoration
    iter_filter_keys = iter(filters_config.keys())
    filters, multi_filter_runtime = load_filter(next(iter_filter_keys))
    # The main loop
    while True:
    
        ret, frame = cap.read()
        if not ret:
            break
        else:    
            points2 = get_landmarks_from_mesh(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
            # if face is partially detected
            if not points2 or (len(points2) != 75):
                continue
    
            # Optical Flow and Stabilization Code
            # 0.05s per frame, the bottleneck is here
            image2Gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
            if isFirstFrame:
                points2Prev = np.array(points2, np.float32)
                image2GrayPrev = np.copy(image2Gray)
                isFirstFrame = False
            # Optical Flow Parameters doesn't help, can't solve the bottleneck
            # lk_params = dict(winSize=(51, 101), maxLevel=10,    
            lk_params = dict(winSize=(101, 101), maxLevel=15,
                            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.001))
            points2Next, st, err = cv2.calcOpticalFlowPyrLK(image2GrayPrev, image2Gray, points2Prev,
                                                            np.array(points2, np.float32),
                                                            **lk_params)
    
            # Final landmark points are a weighted average of detected landmarks and tracked landmarks (that's why we need optical flow)
            for k in range(0, len(points2)):
                d = cv2.norm(np.array(points2[k]) - points2Next[k])
                alpha = math.exp(-d * d / sigma)
                points2[k] = (1 - alpha) * np.array(points2[k]) + alpha * points2Next[k]
                points2[k] = fbc.constrainPoint(points2[k], frame.shape[1], frame.shape[0])
                points2[k] = (int(points2[k][0]), int(points2[k][1]))
    
            # Update variables for next pass
            points2Prev = np.array(points2, np.float32)
            image2GrayPrev = image2Gray
            # End of Optical Flow and Stabilization Code
    
            if VISUALIZE_FACE_POINTS:
                for idx, point in enumerate(points2):
                    cv2.circle(frame, point, 2, (255, 0, 0), -1)
                    cv2.putText(frame, str(idx), point, cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
                cv2.imshow("landmarks", frame)
    
            for idx, filter in enumerate(filters):
    
                filter_runtime = multi_filter_runtime[idx]
                image1 = filter_runtime['image']
                points1 = filter_runtime['points']
                image1_alpha = filter_runtime['image_a']
    
                if filter['morph']:
    
                    hullIndex = filter_runtime['hullIndex']
                    dt = filter_runtime['dt']
                    hull1 = filter_runtime['hull']
    
                    # create copy of frame
                    warped_image = np.copy(frame)
    
                    # Find convex hull
                    hull2 = []
                    for i in range(0, len(hullIndex)):
                        hull2.append(points2[hullIndex[i][0]])
    
                    mask1 = np.zeros((warped_image.shape[0], warped_image.shape[1]), dtype=np.float32)
                    mask1 = cv2.merge((mask1, mask1, mask1))
                    image1_alpha_mask = cv2.merge((image1_alpha, image1_alpha, image1_alpha))
    
                    # Warp the triangles
                    for i in range(0, len(dt)):
                        t1 = []
                        t2 = []
    
                        for j in range(0, 3):
                            t1.append(hull1[dt[i][j]])
                            t2.append(hull2[dt[i][j]])
    
                        fbc.warpTriangle(image1, warped_image, t1, t2)
                        fbc.warpTriangle(image1_alpha_mask, mask1, t1, t2)
    
                    # Blur the mask before blending
                    mask1 = cv2.GaussianBlur(mask1, (3, 3), 10)
    
                    mask2 = (255.0, 255.0, 255.0) - mask1
    
                    # Perform alpha blending of the two images
                    tmp1 = np.multiply(warped_image, (mask1 * (1.0 / 255)))
                    tmp2 = np.multiply(frame, (mask2 * (1.0 / 255)))
                    output = tmp1 + tmp2
                else:
                    dst_points = [points2[int(list(points1.keys())[0])], points2[int(list(points1.keys())[1])]]
                    tform = fbc.similarityTransform(list(points1.values()), dst_points)
                    # Apply similarity transform to input image
                    trans_image = cv2.warpAffine(image1, tform, (frame.shape[1], frame.shape[0]))
                    trans_alpha = cv2.warpAffine(image1_alpha, tform, (frame.shape[1], frame.shape[0]))
                    mask1 = cv2.merge((trans_alpha, trans_alpha, trans_alpha))
    
                    # Blur the mask before blending
                    mask1 = cv2.GaussianBlur(mask1, (3, 3), 10)
    
                    mask2 = (255.0, 255.0, 255.0) - mask1
    
                    # Perform alpha blending of the two images
                    tmp1 = np.multiply(trans_image, (mask1 * (1.0 / 255)))
                    tmp2 = np.multiply(frame, (mask2 * (1.0 / 255)))
                    output = tmp1 + tmp2
    
                frame = output = np.uint8(output)
    
            cv2.imshow("Face Filter", output)
    
            keypressed = cv2.waitKey(1) & 0xFF
            if keypressed == 27:
                break
    
            count += 1

# Frame as input, return the filtered frame
def filtering(frame):
    # startTime = time.time()
    # interval1, interval2 = time.time(), None
    count = 0
    # isFirstFrame = True
    sigma = 50
    # Resize the frame to 320x240 doesn't help much, the bottleneck is in the optical flow
    # frame = cv2.resize(frame, (320, 240))
    # Load an initial filter, I don't have more filter so it's just decoration
    iter_filter_keys = iter(filters_config.keys())
    filters, multi_filter_runtime = load_filter(next(iter_filter_keys))
    # The main loop
    points2 = get_landmarks_from_mesh(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if not points2 or (len(points2) != 75):
        return frame
    # Optical Flow and Stabilization Code, 0.05s per frame, the bottleneck is here
    image2Gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    points2Prev = np.array(points2, np.float32)
    image2GrayPrev = np.copy(image2Gray)
    # Optical Flow Parameters doesn't help
    # lk_params = dict(winSize=(51, 51), maxLevel=10,
    lk_params = dict(winSize=(101, 101), maxLevel=15,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.001))
    points2Next, st, err = cv2.calcOpticalFlowPyrLK(image2GrayPrev, image2Gray, points2Prev,
    np.array(points2, np.float32),
    **lk_params)
    # interval2 = time.time()
    # print("Time for Optical Flow: ", interval2 - interval1)
    # Final landmark points are a weighted average of detected landmarks and tracked landmarks
    for k in range(0, len(points2)):
        d = cv2.norm(np.array(points2[k]) - points2Next[k])
        alpha = math.exp(-d * d / sigma)
        points2[k] = (1 - alpha) * np.array(points2[k]) + alpha * points2Next[k]
        points2[k] = fbc.constrainPoint(points2[k], frame.shape[1], frame.shape[0])
        points2[k] = (int(points2[k][0]), int(points2[k][1]))

    # Update variables for next pass
    points2Prev = np.array(points2, np.float32)
    image2GrayPrev = image2Gray
    # End of Optical Flow and Stabilization Code
    # if VISUALIZE_FACE_POINTS:
    #     for idx, point in enumerate(points2):
    #         cv2.circle(frame, point, 2, (255, 0, 0), -1)
    #         cv2.putText(frame, str(idx), point, cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
    #         cv2.imshow("landmarks", frame)

    for idx, filter in enumerate(filters):
        filter_runtime = multi_filter_runtime[idx]
        image1 = filter_runtime['image']
        points1 = filter_runtime['points']
        image1_alpha = filter_runtime['image_a']

        if filter['morph']:
            hullIndex = filter_runtime['hullIndex']
            dt = filter_runtime['dt']
            hull1 = filter_runtime['hull']   

            # create copy of frame
            warped_image = np.copy(frame)
            # Find convex hull
            hull2 = []
            for i in range(0, len(hullIndex)):
                hull2.append(points2[hullIndex[i][0]])
    
            mask1 = np.zeros((warped_image.shape[0], warped_image.shape[1]), dtype=np.float32)
            mask1 = cv2.merge((mask1, mask1, mask1))
            image1_alpha_mask = cv2.merge((image1_alpha, image1_alpha, image1_alpha))

            # Warp the triangles
            for i in range(0, len(dt)):
                t1 = []
                t2 = []

                for j in range(0, 3):
                    t1.append(hull1[dt[i][j]])
                    t2.append(hull2[dt[i][j]])

                fbc.warpTriangle(image1, warped_image, t1, t2)
                fbc.warpTriangle(image1_alpha_mask, mask1, t1, t2)
            
            # This is a simple filter, so traingles are not the bottleneck
            # def warp_triangle(i):
            #     t1 = [hull1[dt[i][j]] for j in range(3)]
            #     t2 = [hull2[dt[i][j]] for j in range(3)]
            #     fbc.warpTriangle(image1, warped_image, t1, t2)
            #     fbc.warpTriangle(image1_alpha_mask, mask1, t1, t2)
            
            # with ThreadPoolExecutor() as executor:
            #     executor.map(warp_triangle, range(len(dt)))
            # Blur the mask before blending
            mask1 = cv2.GaussianBlur(mask1, (3, 3), 10)
            mask2 = (255.0, 255.0, 255.0) - mask1

            # Perform alpha blending of the two images
            tmp1 = np.multiply(warped_image, (mask1 * (1.0 / 255)))
            tmp2 = np.multiply(frame, (mask2 * (1.0 / 255)))
            output = tmp1 + tmp2
        else:
            dst_points = [points2[int(list(points1.keys())[0])], points2[int(list(points1.keys())[1])]]
            tform = fbc.similarityTransform(list(points1.values()), dst_points)
            # Apply similarity transform to input image
            trans_image = cv2.warpAffine(image1, tform, (frame.shape[1], frame.shape[0]))
            trans_alpha = cv2.warpAffine(image1_alpha, tform, (frame.shape[1], frame.shape[0]))
            mask1 = cv2.merge((trans_alpha, trans_alpha, trans_alpha))
            
            # Blur the mask before blending
            mask1 = cv2.GaussianBlur(mask1, (3, 3), 10)
            mask2 = (255.0, 255.0, 255.0) - mask1

            # Perform alpha blending of the two images
            tmp1 = np.multiply(warped_image, (mask1 * (1.0 / 255)))
            tmp2 = np.multiply(frame, (mask2 * (1.0 / 255)))
            output = tmp1 + tmp2
        
        frame = output = np.uint8(output)
    return frame


if __name__ == "__main__":
    main()