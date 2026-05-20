#import customtkinter as ctk
import os
import webbrowser as wb

wifi= 0
#os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/generate_ssl.py")
#if os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/ip_hostname.py") == 0:
    #wifi = os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/default_wifi.py")
"""app = ctk.CTk()
width = 800
height = 300
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()
x = (screen_width // 2) - (width // 2)
y = (screen_height // 2) - (height // 2)
app.geometry(f"{width}x{height}+{x}+{y}")
app.overrideredirect(True)
app.title("")
app.resizable(False,False)
label = ctk.CTkLabel(app, text="Résilience", font=("Arial", 160, "bold"))
label.place(relx=0.5, rely=0.5, anchor="center")
def animer_histoire():
    app.after(1000, app.destroy)
app.after(7000, animer_histoire)
app.mainloop()"""
#os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/boot/installer.py")
os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/boot/rundb2.py")
os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/boot/redisboot.py")
#os.system("sudo mkdir /run/media/gykhamine/GY")
#os.system("sudo mount /dev/sda1 /run/media/gykhamine/GY")
"""if wifi==1:
##    os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/ip_hostname.py")
    os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/allowed_host.py")
    os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/configurate_firwall.py")
    os.system("rm -f /etc/nginx/nginx.conf")
    os.system("cp /run/media/gykhamine/GY/Gykhamine/conf/nginx/nginx.conf /etc/nginx/nginx.conf")
    os.system("sudo systemctl stop nginx")
    os.system("sudo systemctl start nginx")
else :
    pass"""
os.system("python /run/media/gykhamine/GY/Gykhamine/conf/utils/Gyango/run_server_gunicorn.py")
