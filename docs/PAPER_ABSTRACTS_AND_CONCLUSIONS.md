# Paper Abstracts And Conclusions

Nguon: cac PDF local trong `C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper`.

Ghi chu: File nay tom tat noi dung abstract va conclusion de ho tro proposal/deck cho **FleetIQ Guardian**. Neu dung hinh hoac noi dung truc tiep trong slide nop ra ngoai, can kiem tra license/citation cua tung paper.

## 1. SurroundOcc: Multi-Camera 3D Occupancy Prediction for Autonomous Driving

- **File:** `2303.09551v2.pdf`
- **Authors:** Yi Wei, Linqing Zhao, Wenzhao Zheng, Zheng Zhu, Jie Zhou, Jiwen Lu

### Tom tat abstract

Bai bao de xuat SurroundOcc, mot phuong phap du doan occupancy 3D tu anh multi-camera cho autonomous driving. Thay vi chi dung 3D object detection, SurroundOcc tao bieu dien khong gian day du hon, co the mo ta vat the co hinh dang bat ky va cac lop khong co dinh. Pipeline trich xuat feature da ti le tu tung camera, dung 2D-3D spatial attention de dua feature vao volume 3D, roi dung 3D convolution/deconvolution de tao occupancy prediction. Tac gia cung de xuat quy trinh tao dense occupancy ground truth tu multi-frame LiDAR.

### Tom tat conclusion

Ket luan nhan manh rang multi-camera occupancy prediction co the tao bieu dien moi truong day du hon so voi detection rieng le. Spatial attention va multi-scale supervision giup ket hop feature 2D vao 3D volume hieu qua; pipeline tao dense label giup train occupancy ma khong can annotate thu cong qua dat do.

### Lien quan den FleetIQ Guardian

Rat phu hop cho slide ve **road scene understanding** va lap luan: tu multi-view camera + depth/labels co the tao risk space/occupancy quanh xe, lam nen cho near-miss evidence va collision risk.

## 2. Multi-camera Bird's Eye View Perception for Autonomous Driving

- **File:** `2309.09080v2.pdf`
- **Authors:** David Unger, Nikhil Gosala, Varun Ravi Kumar, Shubhankar Borse, Abhinav Valada, Senthil Yogamani

### Tom tat abstract / mo dau

Day la bai tong quan ve perception tu multi-camera sang Bird's Eye View (BEV) trong autonomous driving. Bai viet giai thich vi sao camera chi cho anh 2D co depth ambiguity, nhung he thong lai can output 3D/BEV de downstream module nhu situation analysis, prediction, planning va control co the su dung. Bai viet tong hop cac task nhu 3D object detection, BEV segmentation, network architecture cho BEV transformation, dataset/metric, va cac thach thuc con mo.

### Tom tat conclusion

Ket luan cho rang BEV la bieu dien quan trong de noi camera perception voi cac tac vu ra quyet dinh. Cac cach tiep can hoc sau co the bien multi-camera perspective view thanh khong gian BEV linh hoat hon IPM truyen thong, nhung van con thach thuc ve depth, geometry, fusion, compute va robustness trong dieu kien thuc te.

### Lien quan den FleetIQ Guardian

Phu hop cho slide **technical feasibility**: giai thich tai sao multi-view camera trong dataset co the duoc chuyen thanh bieu dien top-down/risk timeline cho Fleet Manager thay vi chi xem video raw.

## 3. Cam4DOcc: Benchmark for Camera-Only 4D Occupancy Forecasting in Autonomous Driving Applications

- **File:** `2311.17663v3.pdf`
- **Authors:** Junyi Ma, Xieyuanli Chen, Jiawei Huang, Jingyi Xu, Zhen Luo, Jintao Xu, Weihao Gu, Rui Ai, Hesheng Wang

### Tom tat abstract

Bai bao de xuat Cam4DOcc, benchmark cho camera-only 4D occupancy forecasting. Thay vi chi uoc luong occupancy hien tai, bai bao tap trung vao du doan trang thai khong gian xung quanh trong tuong lai gan. Tac gia xay dung dataset format moi dua tren nuScenes, nuScenes-Occupancy va Lyft-Level5, gom occupancy theo chuoi thoi gian va backward centripetal flow. Bai bao dua ra nhieu baseline va mot network OCFNet cho du doan occupancy 4D end-to-end.

### Tom tat conclusion

Ket luan khang dinh 4D occupancy forecasting la huong quan trong cho autonomous driving vi xe can hieu ca hien tai lan tuong lai gan. OCFNet vuot cac baseline trong nhieu task, va ket qua cho thay end-to-end spatiotemporal network la huong co tiem nang cho camera-only forecasting.

### Lien quan den FleetIQ Guardian

Phu hop cho slide **future vision / stretch goal**: FleetIQ MVP co the bat dau tu TTC/risk hien tai, sau do mo rong sang du bao near-miss va risk trend theo thoi gian.

## 4. Real-Time Sleepiness Detection for Driver State Monitoring System

- **File:** `2504.14807v1.pdf`
- **Authors:** Deepak Ghimire, Sunghwan Jeong, Sunhong Yoon, Sanghyun Park, Juhwan Choi

### Tom tat abstract

Bai bao trinh bay he thong real-time phat hien tinh trang buon ngu cua tai xe bang camera mat. Pipeline phat hien khuon mat, tim vung mat, tracking mat qua cac frame bang normalized cross correlation ket hop Kalman filter, roi dung SVM voi HOG feature de phan loai mat mo/nham. Neu mat bi phat hien nham trong mot khoang thoi gian nhat dinh, he thong xem tai xe dang ngu va kich hoat canh bao.

### Tom tat conclusion

Ket luan cho thay phuong phap dua tren eye-state monitoring co the chay real-time voi chi phi tinh toan thap, phu hop cho moi truong embedded. Tac gia de xuat mo rong tu vung mat sang cac vung khac tren khuon mat de tang kha nang phat hien drowsiness trong tuong lai.

### Lien quan den FleetIQ Guardian

Phu hop cho module **driver-state engine**: in-car camera co the tao signal attention/drowsiness, sau do fusion voi TTC/telemetry de tao compound risk event.

## 5. Real-time Vehicle Distance Estimation Using Single View Geometry

- **File:** `Ali_Real- .pdf`
- **Authors:** Ahmed Ali, Ali Hassan, Afsheen Rafaqat Ali, Hussam Ullah Khan, Wajahat Kazmi, Aamer Zaheer

### Tom tat abstract

Bai bao de xuat cach uoc luong khoang cach xe phia truoc bang single-view geometry thay vi radar/lidar. Phuong phap su dung thong tin hinh hoc cua lane marking, uoc luong horizon bang cross-ratio cua lane boundaries, xac dinh IPM va camera height tu lane width, roi back-project diem anh xuong road plane de tinh khoang cach. Tac gia danh gia tren KITTI, nuScenes va Lyft Level 5, so sanh voi radar va monocular depth learning.

### Tom tat conclusion

Ket luan nhan manh phuong phap hinh hoc co chi phi tinh toan thap, khong phu thuoc manh vao domain du lieu va co the chay real-time. Du khong phai luc nao vuot supervised deep learning, cach nay huu ich cho ADAS/fleet vi de tich hop voi lane/vehicle detection va co kha nang hoat dong thuc dung.

### Lien quan den FleetIQ Guardian

Rat phu hop cho **TTC engine**: FleetIQ co the giai thich distance/TTC bang ROI lead vehicle + depth/geometry + temporal smoothing, thay vi noi chung chung "AI do khoang cach".

## 6. Visual, Auditory, and Audiovisual Time-to-Collision Estimation Among Participants With Age-Related Macular Degeneration Compared to a Normal-Vision Group: The TTC-AMD Study

- **File:** `journal.pone.0337549.pdf`
- **Authors:** Patricia R. DeLucia, Daniel Oberfeld, Joseph K. Kearney, Melissa Cloutier, Anna M. Jilla, Avery Zhou, Stephanie Trejo Corona, Jessica Cormier, Audrey Taylor, Charles C. Wykoff, Robin Baures

### Tom tat abstract

Bai bao nghien cuu cach con nguoi uoc luong time-to-collision (TTC) khi co cue thi giac, thinh giac hoac ca hai, so sanh nhom co thoai hoa diem vang theo tuoi voi nhom thi luc binh thuong. Thi nghiem dung moi truong VR voi xe dang tien lai gan nguoi tham gia. Ket qua cho thay ca visual va auditory cues deu anh huong den TTC judgment; nhom suy giam thi luc dat hieu nang tuong duong theo mot so chi so nhung trong so thong tin su dung co khac biet.

### Tom tat conclusion

Ket luan cho rang TTC estimation khong chi phu thuoc vao mot nguon tin hieu duy nhat. Ca nhom normal vision va impaired vision deu ket hop nhieu cue de uoc luong va cham, nhung cach gan trong so cho distance, optical size, auditory cue co khac nhau. Dieu nay nhan manh vai tro cua multi-cue fusion trong danh gia collision risk.

### Lien quan den FleetIQ Guardian

Phu hop cho slide **risk intelligence**: TTC la mot chi so an toan quan trong, nhung he thong tot nen fusion nhieu signal va gan confidence thay vi trigger alert tu mot nguong don le.

## 7. Intelligent Driver Monitoring Systems: A Survey of Drowsiness Detection Technologies for Road Safety

- **File:** `s10462-026-11505-w.pdf`
- **Authors:** Osama F. Hassan, Ahmed F. Ibrahim, M. A. Makhlouf, B. Hafiz, Ahmed Gomaa

### Tom tat abstract

Bai survey tong hop cac cong nghe driver drowsiness monitoring giai doan 2020-2025, bao gom image/video, physiological signals, vehicle behavior va multimodal fusion. Bai viet chi ra vision method da chuyen tu classical pipeline sang deep learning/Transformer; physiological signal on dinh hon trong mot so dieu kien nhung can them hardware; multimodal fusion tang do ben vung nhung tang compute/integration burden. Bai viet cung nhan manh van de evaluation: subject-dependent test co the thoi phong accuracy, can dung metric nhu PR-AUC, recall tai false-alarm rate co dinh, calibration va time-to-detect.

### Tom tat conclusion

Ket luan nhan manh DMS phai duoc danh gia theo metric gan voi van hanh that, khong chi accuracy. Tac gia khuyen dung prevalence-aware evaluation, PR curve, fixed false-alarm operating points, calibration va benchmark minh bach. Cac van de privacy, edge processing, regulation va cross-dataset validation cung la dieu kien quan trong de dua DMS vao xe/fleet thuc te.

### Lien quan den FleetIQ Guardian

Rat phu hop cho slide **why our scoring is explainable and robust**: FleetIQ nen trinh bay driver-state signal voi confidence, false-alarm control va event evidence, khong chi khoe accuracy.

## 8. Optimized Driver Fatigue Detection Method Using Multimodal Neural Networks

- **File:** `s41598-025-86709-1.pdf`
- **Authors:** Shengli Cao, Peihua Feng, Wei Kang, Zeyi Chen, Bo Wang

### Tom tat abstract

Bai bao de xuat phuong phap phat hien fatigue bang multimodal neural networks tren DROZY dataset, ket hop physiological signals va facial images. Hai kieu model duoc danh gia: feature combination va feature coupled. Diem chinh la model feature-coupled, trong do feature tu cac modality co vai tro nhu mutual weights de anh huong lan nhau truoc khi du doan fatigue. Model dat metric cao va dung majority voting o buoc decision de tang tinh on dinh.

### Tom tat conclusion

Ket luan cho rang multimodal feature coupling giup phat hien fatigue tot hon so voi chi ket hop feature don gian. Cac ablation study cho thay tung thanh phan nhu LSTM, ResNet18 va coupling mechanism deu dong gop vao hieu nang. Bai bao goi y multimodal fusion la huong manh cho real-time fatigue detection trong xe.

### Lien quan den FleetIQ Guardian

Phu hop cho **fusion story**: FleetIQ khong can train model nang trong MVP, nhung co the pitch logic fusion tu driver state + vehicle behavior + road risk theo tinh than multimodal.

## 9. Real Time Speed Estimation of Moving Vehicles from Side View Images from an Uncalibrated Video Camera

- **File:** `sensors-10-04805.pdf`
- **Authors:** Sedat Dogan, Mahir Serhan Temiz, Sitki Kulur

### Tom tat abstract

Bai bao giai quyet bai toan uoc luong toc do xe tu side-view video camera chua calibration. Phuong phap chon cac diem tham chieu tren xe, track qua nhieu frame, tinh displacement vector theo pixel va thoi gian, sau do chuyen tu image space sang object space bang thong tin calibration/orientation. Tac gia de xuat giai phap cho van de speed estimation trong traffic monitoring bang video.

### Tom tat conclusion

Ket luan cho thay sparse optical flow hieu qua cho uoc luong toc do real-time cua xe, voi sai so duoc bao cao khoang +/-1.12 km/h trong thiet lap cua bai bao. Phuong phap co the mo rong cho nhieu xe neu them phan phan cum vector theo tung xe, va co tiem nang trong ADAS/sensor network.

### Lien quan den FleetIQ Guardian

Phu hop cho **telemetry/road-risk feature extraction**: neu can suy ra relative motion hoac validate speed/closing trend tu video, optical-flow-style tracking la mot baseline de giai thich.

## 10. Early Drowsiness Detection via Second-Order Derivative Analysis of Heart Rate Variability: A Non-Contact ECG Approach with Machine Learning

- **File:** `sensors-26-01348.pdf`
- **Authors:** Fabrice Vaussenat, Abhiroop Bhattacharya, Julie Payette, Alireza Saidi, Victor Bellemin, Geordi-Gabriel Renaud-Dumoulin, Sylvain G. Cloutier, Ghyslain Gagnon

### Tom tat abstract

Bai bao nghien cuu phat hien drowsiness som bang HRV derivatives tu ECG khong tiep xuc gan trong ghe. Tac gia dat cau hoi lieu first/second derivatives cua HRV co the phat hien pre-crash state som hon cue hanh vi hay khong. Thi nghiem gom 25 nguoi, 49 phien driving simulator, 1591 crash va 6.78 trieu datapoint. Ket qua cho thay HRV derivative mot minh khong du manh, nhung bo sung gia tri khi ket hop voi feature khac; detection bang derivative co the xuat hien truoc bieu hien hanh vi 5-8 phut va truoc crash khoang 6.8 phut.

### Tom tat conclusion

Ket luan nhan manh tin hieu sinh ly co tiem nang phat hien som trang thai suy giam truoc khi bieu hien thanh hanh vi nguy hiem, nhung can fusion voi driving performance va feature khac de dat do tin cay cao. Non-contact ECG cung co loi the privacy so voi camera-only monitoring.

### Lien quan den FleetIQ Guardian

Phu hop cho **stretch/future vision**: MVP co in-car camera va telemetry, nhung kien truc fusion co the mo rong sang signal sinh ly/non-contact sensor neu OEM cung cap.

## 11. 6D-VNet: End-to-End 6DoF Vehicle Pose Estimation from Monocular RGB Images

- **File:** `Wu_6D-VNet_End-To-End_6-DoF_Vehicle_Pose_Estimation_From_Monocular_RGB_Images_CVPRW_2019_paper.pdf`
- **Authors:** Di Wu, Zhaoyong Zhuang, Canqun Xiang, Wenbin Zou, Xia Li

### Tom tat abstract

Bai bao gioi thieu 6D-VNet, framework end-to-end de uoc luong 6DoF pose cua xe tu anh RGB monocular. Phuong phap mo rong Mask R-CNN voi cac head rieng cho vehicle class, rotation va translation. Tac gia nhan manh translation regression rat quan trong trong autonomous driving vi khoang cach theo truc doc thay doi lon. Bai bao cung them non-local block bien doi de khai thac quan he giua cac traffic participants.

### Tom tat conclusion

Ket luan cho thay viec hoc end-to-end detection + rotation + translation co the uoc luong pose xe tot hon so voi pipeline tach roi, nhat la trong bai toan autonomous driving can hieu quan he 3D giua cac agent. Non-local/context modeling giup cai thien viec suy luan pose trong scene co nhieu xe.

### Lien quan den FleetIQ Guardian

Phu hop cho slide **future technical depth**: FleetIQ khong bat buoc can 6DoF pose trong MVP, nhung vehicle pose/orientation co the la extension de cai thien near-miss severity, lane-change/cut-in detection va evidence visualization.

## GoI y dung paper trong proposal

- **Architecture / camera-only scene understanding:** SurroundOcc, BEV Perception, Cam4DOcc.
- **TTC / distance / collision risk:** Real-time Vehicle Distance Estimation, TTC-AMD Study, Speed Estimation from Video.
- **Driver state / DMS:** Real-Time Sleepiness Detection, DMS Survey, Multimodal Fatigue Detection, HRV Drowsiness Detection.
- **Vehicle pose extension:** 6D-VNet.

## Trang thai extract hinh

Hinh anh da duoc extract vao:

`C:\Users\admin\Documents\Projects\AutomotiveHacathon\paper\extracted_figures`

File tra cuu:

- `manifest.csv`
- `contact_sheets\caption_crops_contact_sheet.jpg`
- `contact_sheets\embedded_images_contact_sheet.jpg`
