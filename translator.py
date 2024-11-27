import cv2
import mediapipe as mp
import math
import threading
import time
import tkinter as tk
import queue

def get_coordinates(landmark_number, frame, hand_index, results):
    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            if handedness.classification[0].label == ("Right" if hand_index == 0 else "Left"):
                if 0 <= landmark_number < len(hand_landmarks.landmark):
                    landmark = hand_landmarks.landmark[landmark_number]
                    height, width, _ = frame.shape
                    return int(landmark.x * width), int(landmark.y * height)
    return None

def get_angle(a, b, c):
    ab = math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    bc = math.sqrt((b[0] - c[0]) ** 2 + (b[1] - c[1]) ** 2)
    ac = math.sqrt((a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2)
    
    if ab == 0 or bc == 0 or ac == 0:
        return 180 

    try:
        angle = math.acos((ab**2 + bc**2 - ac**2) / (2 * ab * bc))
    except ValueError:
        return 180  
    return angle * 180 / math.pi


def is_bent(a, b, c, frame, hand_index, results):
    tip = get_coordinates(a, frame, hand_index, results)
    middle = get_coordinates(b, frame, hand_index, results)
    bottom = get_coordinates(c, frame, hand_index, results)
    if tip and middle and bottom:
        angle = get_angle(tip, middle, bottom)
        return angle < 160 
    return False


mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
cap = cv2.VideoCapture(0)

finger_states = [0] * 8

def rindex(frame, results):
    finger_states[4] = 0 if is_bent(8, 6, 5, frame, 0, results) else 1  # right index
    finger_states[5] = 0 if is_bent(12, 10, 9, frame, 0, results) else 1  # right middle
    finger_states[6] = 0 if is_bent(16, 14, 13, frame, 0, results) else 1  # right ring
    finger_states[7] = 0 if is_bent(20, 18, 17, frame, 0, results) else 1  # right pinky

def lindex(frame, results):
    finger_states[3] = 0 if is_bent(8, 6, 5, frame, 1, results) else 1  # left pinky
    finger_states[2] = 0 if is_bent(12, 10, 9, frame, 1, results) else 1  # left ring
    finger_states[1] = 0 if is_bent(16, 14, 13, frame, 1, results) else 1  # left middle
    finger_states[0] = 0 if is_bent(20, 18, 17, frame, 1, results) else 1  # left index


def is_wrist_visible(frame, hand_index, results):
    wrist = get_coordinates(0, frame, hand_index, results)
    return wrist is not None


def print_finger_states(stop_event, update_gui_callback, frame_queue):
    prevchar = "A"
    counter = 0
    current_char = ""
    sentence = ""
    while not stop_event.is_set():
        time.sleep(0.75)


        if not frame_queue.empty():
            frame, results = frame_queue.get()

            num = 0
            for i in range(8):
                if finger_states[i] == 1:
                    num += 2**i
            char = chr(num)

            if prevchar == char:
                counter += 1
            else:
                counter = 0


            if is_wrist_visible(frame, 0, results) and is_wrist_visible(frame, 1, results):
                if counter == 3:
                    sentence += char
                    counter = 0
            current_char = char
            update_gui_callback(sentence, current_char)
            prevchar = char


def process_frame(stop_event, frame_queue):
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        frame = cv2.flip(frame, 1)

        if results.multi_hand_landmarks:
            rindex(frame, results)
            lindex(frame, results)

        frame_queue.put((frame, results))

        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_event.set()
            break
#below is chatgpt
# Tkinter GUI to display the sentence
class FingerSpellingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Finger Spelling")
        
        self.label = tk.Label(root, text="Spelled Sentence: ", font=("Arial", 24))
        self.label.pack(pady=20)

        self.sentence_var = tk.StringVar()
        self.sentence_label = tk.Label(root, textvariable=self.sentence_var, font=("Arial", 20))
        self.sentence_label.pack(pady=20)

        self.current_letter_var = tk.StringVar()
        self.current_letter_label = tk.Label(root, textvariable=self.current_letter_var, font=("Arial", 20))
        self.current_letter_label.pack(pady=20)

    def update_sentence(self, sentence, current_char):
        self.sentence_var.set(sentence)
        self.current_letter_var.set(f"Current Letter: {current_char}")

def start_gui():
    root = tk.Tk()
    app = FingerSpellingApp(root)
    return root, app
#no chatgpt here
if __name__ == "__main__":
    root, app = start_gui()

    stop_event = threading.Event() 
    frame_queue = queue.Queue(maxsize=1)

    processing_thread = threading.Thread(target=process_frame, args=(stop_event, frame_queue))
    printing_thread = threading.Thread(target=print_finger_states, args=(stop_event, app.update_sentence, frame_queue))
    
    processing_thread.start()
    printing_thread.start()


    root.mainloop()

    processing_thread.join()  
    printing_thread.join()
    
    cap.release()
    cv2.destroyAllWindows()
