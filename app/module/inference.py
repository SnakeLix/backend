import os
import tensorflow as tf

from skimage import io
from imutils.object_detection import non_max_suppression

import numpy as np
import math
import time
import cv2
import string

def getDetBoxes_core(textmap, linkmap, text_threshold, link_threshold, low_text):
    # prepare data
    linkmap = linkmap.copy()
    textmap = textmap.copy()
    img_h, img_w = textmap.shape

    """ labeling method """
    ret, text_score = cv2.threshold(textmap, low_text, 1, 0)
    ret, link_score = cv2.threshold(linkmap, link_threshold, 1, 0)

    text_score_comb = np.clip(text_score + link_score, 0, 1)
    nLabels, labels, stats, centroids = cv2.connectedComponentsWithStats(text_score_comb.astype(np.uint8), connectivity=4)

    det = []
    mapper = []
    for k in range(1,nLabels):
        # size filtering
        size = stats[k, cv2.CC_STAT_AREA]
        if size < 10: continue

        # thresholding
        if np.max(textmap[labels==k]) < text_threshold: continue

        # make segmentation map
        segmap = np.zeros(textmap.shape, dtype=np.uint8)
        segmap[labels==k] = 255
        segmap[np.logical_and(link_score==1, text_score==0)] = 0   # remove link area
        x, y = stats[k, cv2.CC_STAT_LEFT], stats[k, cv2.CC_STAT_TOP]
        w, h = stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT]
        niter = int(math.sqrt(size * min(w, h) / (w * h)) * 2)
        sx, ex, sy, ey = x - niter, x + w + niter + 1, y - niter, y + h + niter + 1
        # boundary check
        if sx < 0 : sx = 0
        if sy < 0 : sy = 0
        if ex >= img_w: ex = img_w
        if ey >= img_h: ey = img_h
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(1 + niter, 1 + niter))
        segmap[sy:ey, sx:ex] = cv2.dilate(segmap[sy:ey, sx:ex], kernel)

        # make box
        np_contours = np.roll(np.array(np.where(segmap!=0)),1,axis=0).transpose().reshape(-1,2)
        rectangle = cv2.minAreaRect(np_contours)
        box = cv2.boxPoints(rectangle)

        # align diamond-shape
        w, h = np.linalg.norm(box[0] - box[1]), np.linalg.norm(box[1] - box[2])
        box_ratio = max(w, h) / (min(w, h) + 1e-5)
        if abs(1 - box_ratio) <= 0.1:
            l, r = min(np_contours[:,0]), max(np_contours[:,0])
            t, b = min(np_contours[:,1]), max(np_contours[:,1])
            box = np.array([[l, t], [r, t], [r, b], [l, b]], dtype=np.float32)

        # make clock-wise order
        startidx = box.sum(axis=1).argmin()
        box = np.roll(box, 4-startidx, 0)
        box = np.array(box)

        det.append(box)
        mapper.append(k)

    return det, labels, mapper

def adjustResultCoordinates(polys, ratio_w, ratio_h, ratio_net = 2):
    if len(polys) > 0:
        polys = np.array(polys)
        for k in range(len(polys)):
            if polys[k] is not None:
                polys[k] *= (ratio_w * ratio_net, ratio_h * ratio_net)
    return polys
  
# Postprocessing output from craft TFLite Model
def postprocess_craft(y, feature, image):
    score_text = y[0,:,:,0]
    score_link = y[0,:,:,1]
    text_threshold = 0.7
    link_threshold = 0.4
    low_text = 0.4
    ratio_w = ratio_h = 1
    boxes, labels, mapper = getDetBoxes_core(score_text, score_link, text_threshold, link_threshold, low_text)
    polys = [None] * len(boxes)
    boxes = adjustResultCoordinates(boxes, ratio_w, ratio_h)
    for k in range(len(polys)):
        if polys[k] is None: polys[k] = boxes[k]
    output_image = image[:,:,::-1].copy()
    crops = list()
    for i, box in enumerate(polys):
        poly = np.array(box).astype(np.int32).reshape((-1))
        poly = poly.reshape(-1, 2)
        min_co = tuple(np.min(poly, axis=0))
        max_co = tuple(np.max(poly, axis=0))
        cv2.rectangle(output_image, min_co, max_co, (0, 0, 255), 2)
        crops.append([min_co, max_co])
    return output_image, crops

def tflite_inference(input):
    model_name = "./crnn_float16.tflite"
    interpreter = tf.lite.Interpreter(model_path=model_name)
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.allocate_tensors()
    interpreter.set_tensor(input_details[0]['index'], input)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    return output

def ctc_decode(preds):
    pred_index = np.argmax(preds, axis=2)
    # char_list = list(opt.character)
    char_list = list("0123456789abcdefghijklmnopqrstuvwxyz")
    char_dict = {}
    for i, char in enumerate(char_list):
        char_dict[char] = i + 1
    char_list = ['_'] + char_list
    BLANK = 0
    texts = []
    output = pred_index[0, :]
    characters = []
    for i in range(preds.shape[1]):
        if output[i] != BLANK and (not (i > 0 and output[i - 1] == output[i])):
            characters.append(char_list[output[i]])
        text = ''.join(characters)
    return text

import concurrent.futures
import numpy as np
import cv2
import tensorflow as tf
from skimage import io

class TensorflowLiteOCR:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        craft_model_path = os.path.join(base_dir, 'craft_float_800.tflite')
        crnn_model_path = os.path.join(base_dir, 'crnn_dr.tflite')
        self.craft_float_model = tf.lite.Interpreter(model_path=craft_model_path)
        self.craft_float_model.allocate_tensors()
        self.crnn_float_model = tf.lite.Interpreter(model_path=crnn_model_path)
        self.crnn_float_model.allocate_tensors()

    def crnn_inference(self, input, interpreter):
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        interpreter.set_tensor(input_details[0]['index'], input)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])
        return output

    def ctc_decode(self, preds):
        pred_index = np.argmax(preds, axis=2)
        char_list = list("0123456789abcdefghijklmnopqrstuvwxyz")
        char_dict = {char: i + 1 for i, char in enumerate(char_list)}
        char_list = ['_'] + char_list
        BLANK = 0
        texts = []
        output = pred_index[0, :]
        characters = []
        for i in range(preds.shape[1]):
            if output[i] != BLANK and (not (i > 0 and output[i - 1] == output[i])):
                characters.append(char_list[output[i]])
        text = ''.join(characters)
        return text

    def craft_preprocess(self, image_path):
        image = io.imread(image_path)
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        if image.shape[2] == 1:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

        image = np.array(image).astype(np.float32)
        input_image = cv2.resize(image, dsize=(600, 800), interpolation=cv2.INTER_LINEAR)
        store_input_image = input_image.copy()
        mean = (0.485, 0.456, 0.406)
        variance = (0.229, 0.224, 0.225)
        input_image -= np.array([mean[0] * 255.0, mean[1] * 255.0, mean[2] * 255.0], dtype=np.float32)
        input_image /= np.array([variance[0] * 255.0, variance[1] * 255.0, variance[2] * 255.0], dtype=np.float32)
        image = np.transpose(input_image, (2, 0, 1))
        preprocessed_image = image[np.newaxis]
        return store_input_image, preprocessed_image

    def craft_tflite_model(self, input_data):
        interpreter = self.craft_float_model
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        y = interpreter.get_tensor(output_details[0]['index'])
        feature = interpreter.get_tensor(output_details[1]['index'])
        return y, feature

    def ocr_model(self, image, model):
        if model == 'crnn':
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image = image / 127.5 - 1.0
            image = cv2.resize(image, (100, 32), interpolation=cv2.INTER_CUBIC)
            image = np.expand_dims(image, 0)
            image = np.expand_dims(image, 0)
            image = np.float32(image)

            # Create a new interpreter for each thread
            base_dir = os.path.dirname(os.path.abspath(__file__))
            crnn_model_path = os.path.join(base_dir, 'crnn_dr.tflite')
            interpreter = tf.lite.Interpreter(model_path=crnn_model_path)
            text = self.crnn_inference(image, interpreter)
            decoded_text = self.ctc_decode(text)
            return decoded_text
        return None

    def process_box(self, box, input_image, index):
        cropped_image = input_image[box[0][1]:box[1][1], box[0][0]:box[1][0], :]
        final_output = self.ocr_model(cropped_image, 'crnn')
        return (index, box, final_output)

    def run(self, image_path):
        input_image, preprocessed_image = self.craft_preprocess(image_path)
        y, feature = self.craft_tflite_model(preprocessed_image)
        output, crops = postprocess_craft(y, feature, input_image)
        final_text = ""
        boxes_with_labels = []
        # Using ThreadPoolExecutor for multi-threaded inference, while preserving order
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.process_box, box, input_image, index) for index, box in enumerate(crops)]
            results = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        # Sort results based on the original indices to maintain the order
        results.sort(key=lambda x: x[0])
        # Collect the final results in order
        for _, box, final_output in results:
            if final_output:
                final_text += final_output + " "
                # Convert all numpy types to Python native types for JSON serialization
                box_py = [[int(x), int(y)] for (x, y) in box]
                boxes_with_labels.append({'box': box_py, 'label': final_output})
        return {'final_text': final_text.strip(), 'boxes': boxes_with_labels}


def run_ocr_on_image_path(image_path: str):
    """
    Run OCR on an image from a file path. Returns dict with 'final_text' and 'boxes'.
    """
    ocr = TensorflowLiteOCR()
    return ocr.run(image_path)


def run_ocr_on_image_array(image_array: np.ndarray):
    """
    Run OCR on an image from a numpy array (BGR or RGB). Returns dict with 'final_text' and 'boxes'.
    """
    import tempfile
    import os
    # Save to a temporary file for compatibility
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        cv2.imwrite(tmp.name, image_array)
        tmp_path = tmp.name
    try:
        ocr = TensorflowLiteOCR()
        result = ocr.run(tmp_path)
    finally:
        os.remove(tmp_path)
    return result