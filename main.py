from comfyui_api import ComfyUIClient
import time

# 主函数
if __name__ == "__main__":

    client = ComfyUIClient()

    image_path = 'https://ts1.cn.mm.bing.net/th/id/R-C.eed97557f689df2382b6a9fc85ed172e?rik=d%2fBN9fsXJ2nz2w&riu=http%3a%2f%2fup.bizhizu.com%2fpic%2fd1%2fb7%2fc1%2fd1b7c1c9d4362b4ed5a433e69a19b383.jpg&ehk=OafBZEPbO07cQidzqmNBh0FzR5lM78gdhBOg7%2bjNdis%3d&risl=&pid=ImgRaw&r=0'
    
    # image_path = 'https://k.sinaimg.cn/www/dy/slidenews/24_img/2016_19/74485_1363976_499220.jpg/w640slw.jpg'

    face_image_path = 'https://k.sinaimg.cn/www/dy/slidenews/24_img/2016_19/74485_1363976_499220.jpg/w640slw.jpg'
    
    task_id = '9eae9df7-eac6-4c0d-9df9-e7f4f83f8ba1'
    work_id = '1'

    # 记录开始时间
    start_time = time.time()

    # 客片换脸
    result = client.process_face_swap_thumbnail(image_path, face_image_path)
    print(result)

    # result = client.process_face_swap(task_id, work_id)
    # print(result)

    # # 客片人脸脱敏
    # result = client.process_face_desensitization_thumbnail(image_path)
    # print(result)

    # result = client.process_face_desensitization(task_id, work_id)
    # print(result)

    # result = client.process_image_upscale(task_id)
    # print(result)

    # image_path = 'https://www.jiaphoto.net/Public/upload/2019-06-18/5d085600a806e.jpg'
    # image_path = 'https://ts1.cn.mm.bing.net/th/id/R-C.63fe5d4a3b0d4fe29a39cc24d80d63c8?rik=%2f5S7WyLaiRlm8A&riu=http%3a%2f%2fcdn.muxi520.com%2f2022-06-24%2fcky5rvxfxjobra1zm7.jpg&ehk=DtjWIrLVKeInWT3YX%2bWZUd9Rg%2fKUGAwki6wVJuiYgH8%3d&risl=&pid=ImgRaw&r=0'
    
    # face_image_path = 'https://ts1.cn.mm.bing.net/th/id/R-C.5f10d21d142995f1e28c791d9a8fdc24?rik=WMQ89o3a%2bYYq5Q&riu=http%3a%2f%2fp1.qhimg.com%2ft010e22b8490821150f.jpg%3f1200*800&ehk=hqeRq5HPWFHQTJvCHcmKkVT3RM9RSS8oQgiVx6Wq%2fOU%3d&risl=&pid=ImgRaw&r=0'
    
    # order = [1, 2] 
    
    # result = client.process_multiple_face_swap_fast(image_path, face_image_path)
    # print(result)

    # result = client.process_multiple_face_desensitization_fast(image_path)
    # print(result)

    # result = client.process_multiple_face_swap(image_path, face_image_path, order)
    # print(result) 

    # result = client.process_multiple_face_desensitization(image_path, order)
    # print(result)

    # result = client.process_multiple_face_desensitization_auto(image_path)
    # print(result)
    
    # result = client.process_face_swap_auto(image_path, face_image_path)
    # print(result)

    # 记录结束时间
    end_time = time.time()

    # 计算耗时
    elapsed_time = end_time - start_time

    print(f"耗时: {elapsed_time:.2f} 秒")