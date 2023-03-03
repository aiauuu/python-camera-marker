import cv2

cap = cv2.VideoCapture(0)

# cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
cap.read()
cap.set(cv2.CAP_PROP_EXPOSURE, 1)
cap.read()