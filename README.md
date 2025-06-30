## Main steps
**Robocar**<br/>
- Run server<br/>
- Video streaming<br/>

**Desktop**<br/>
- Receive camera streaming stream from Robocar<br/>
- Extract class and bbox information from Robocar<br/>
- Additionally, receive speed of Robocar<br/>


### 1. Run Flask server (Robocar)
```
$ python flask_server.py
```
<br/>

### 2. YOLO Detection (Desktop)
```
$ python desktop_yolo_stream.py
```
<br>

