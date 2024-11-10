from compreface import CompreFace
from compreface.service import RecognitionService
from compreface.collections import FaceCollection
from compreface.collections.face_collections import Subjects

DOMAIN: str = 'http://localhost'
PORT: str = '8000'
API_KEY: str = 'f3dd0089-1396-4b69-8054-bfa6fee40d8f'

compre_face: CompreFace = CompreFace(DOMAIN, PORT)
recognition: RecognitionService = compre_face.init_face_recognition(API_KEY)
face_collection: FaceCollection = recognition.get_face_collection()
subjects: Subjects = recognition.get_subjects()


def add_face(image_path: str, subject: str):
    """将人脸图像添加到集合中"""
    try:
        # 获取所有现有主体
        existing_subjects = subjects.list()
        print("现有主体列表:", existing_subjects)  # 调试输出

        # 检查主体是否已存在
        subject_names = existing_subjects.get('subjects', [])
        if subject not in subject_names:
            subjects.add(subject)
            print(f"添加新主体: {subject}")

        # 将图像添加到人脸集合
        result = face_collection.add(image_path=image_path, subject=subject)
        print(f"成功将人脸 '{subject}' 添加到集合中:", result)

    except Exception as e:
        print(f"添加人脸失败: {e}")
