import os
from contextlib import contextmanager
from functools import partial
import urllib.request
from bs4 import BeautifulSoup as BS
import re
from pytube import YouTube
import glob
import subprocess
import random
import cv2
import imageio
import moviepy
from moviepy.editor import *
import moviepy.audio.fx.all as afx

# Enters the specified directory and goes back to the previous directory once closed
@contextmanager
def cwd(path):
    oldpwd=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


class MusicQuizCreator:
    def __init__(self, ffmpeg_tools_path):
        self.ffmpeg_tools_path = ffmpeg_tools_path
        self.root_path = os.getcwd()
        self.create_dirs()

    def create_dirs(self):
        subfolders = ('Videos/full_videos', 'Videos/cut_videos', 'Videos/complete_videos')
        concat_path = partial(os.path.join, self.root_path)
        makedirs = partial(os.makedirs, exist_ok=True)
        for path in map(concat_path, subfolders):
            makedirs(path)

    def create_readme(self):
        pass

    def check_if_file_exists(self, filename):
        if os.path.isfile(filename):
            return True
        return False

    def youtube_first_result(self, text_to_search):
        query = urllib.parse.quote(text_to_search)
        html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + query)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())

        # Make sure the video is no longer than 10 minutes. Tries the first 3 results
        for i in range(3):
            youtube_video = urllib.request.urlopen('https://www.youtube.com/watch?v=' + video_ids[i])
            soup = BS(youtube_video, "html.parser")
            vid_length = soup.find('meta', itemprop='duration')['content']
            min_in_sec = int(re.sub("[^0-9]", "", vid_length.split("M")[0])) * 60
            sec = int(re.sub("[^0-9]", "", vid_length.split("M")[1]))
            if min_in_sec + sec < (10 * 60):
                return 'https://www.youtube.com/watch?v=' + video_ids[i]
        return False

    def download_youtube_video(self, txt_name, txt_path):
        self.yt_download_txt_list = txt_name
        self.yt_download_txt_path = txt_path
        videos_to_download = self.load_youtube_download_txt_list()

        with cwd(self.root_path + '/Videos/full_videos/'):
            for video_name in videos_to_download:
                if self.check_if_file_exists(video_name+'.mp4'):
                    print(video_name + '.mp4 already exists, skipping..')
                    continue
                print(f'Finding: {video_name}')
                for i in range(10):
                    try:
                        ytube_url = self.youtube_first_result(video_name)
                        yt = YouTube(ytube_url)
                        # Only 720 and below, otherwise you have to DL audio and video seperately and merge them
                        stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
                        print(f'Downloading: {video_name}..')
                        stream.download(filename=video_name)
                        break
                    except KeyError as e:
                        print(f'Got KeyError {e}. Trying again {i+1}/10..')

    def load_youtube_download_txt_list(self):
        with cwd(self.yt_download_txt_path):
            with open(self.yt_download_txt_list, encoding='utf-8') as f:
                content = f.readlines()

        list_of_vid_names = []
        # Removes any special characters besides space and -, and removes multiple spacing
        for vid_name in content:
            vid_name = vid_name.strip()
            vid_name = re.sub("[^a-zA-Z0-9-:space:]", " ", vid_name)
            vid_name = re.sub(' +', ' ', vid_name)
            list_of_vid_names.append(vid_name)
        return list_of_vid_names

    def fetch_mp4_files(self, path):
        videos = []
        with cwd(path):
            for filename in glob.glob('*.mp4'):
                videos.append(filename)
        return videos

    def get_video_length(self, filename, video_read_path):
        with cwd(self.ffmpeg_tools_path):
            result = subprocess.run(["ffprobe.exe", "-v", "error", "-show_entries",
                                     "format=duration", "-of",
                                     "default=noprint_wrappers=1:nokey=1", video_read_path + filename],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        return float(result.stdout)

    def timer_text_overlay_ffmpeg_input_strings(self, video_name):
        # Crude way to ensure text can fit on screen
        if len(video_name) > 100:
            font_size = '16'
        elif len(video_name) > 70:
            font_size = '22'
        else:
            font_size = '32'

        video_fade = "[0:0][1:0]overlay=enable='between(t,0,10)'[out]"
        result_txt = f"drawtext=enable='between(t,10,21)': fontfile={self.font_path}/{self.font_name}: " \
                     f"text={video_name}: fontcolor=white: fontsize={font_size}: box=1: boxcolor=black@0.5: " \
                     f"boxborderw=5: x=50: y=h-text_h-50"
        return video_fade, result_txt

    def get_height_width(self, filename):
        vid = cv2.VideoCapture(filename)
        return vid.get(cv2.CAP_PROP_FRAME_WIDTH), vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def scale_video_width_height(self, video, path, scaling):
        scale = subprocess.call(["ffmpeg.exe",
                                 "-i", path+video,
                                 '-vf', scaling,
                                 '-c:a', 'copy',
                                 path+'resized'+video])

    def cut_videos(self, countdown_overlay_name, font_name, countdown_overlay_path, font_path):
        overlay_resized = False
        scaling = "[in]scale=iw*min(1280/iw\,720/ih):ih*min(1280/iw\,720/ih)[scaled]; " \
                  "[scaled]pad=1280:720:(1280-iw*min(1280/iw\,720/ih))/2:(720-ih*min(1280/iw\,720/ih))/2[padded]; " \
                  "[padded]setsar=1:1[out]"
        self.countdown_overlay_name = countdown_overlay_name
        self.font_name = font_name
        self.countdown_overlay_path = countdown_overlay_path
        self.font_path = font_path
        video_list = self.fetch_mp4_files(self.root_path + '/Videos/full_videos/')
        cut_length = 21.0
        with cwd(self.ffmpeg_tools_path):
            o_w, o_h = self.get_height_width(f'{self.countdown_overlay_path}/{self.countdown_overlay_name}')
            if o_w != 1280 or o_h != 720:
                self.scale_video_width_height(video=self.countdown_overlay_name, path=countdown_overlay_path + '/',
                                              scaling=scaling)
                self.countdown_overlay_name = 'resized'+self.countdown_overlay_name
                overlay_resized = True

            for video in video_list:
                vid_duration = self.get_video_length(video, self.root_path + '/Videos/full_videos/')
                trim_start = random.uniform(cut_length, vid_duration)

                if self.check_if_file_exists(filename=self.root_path + '/Videos/cut_videos/' + video):
                    print(f'Video: {video} has already been trimmed. Skipping..')
                    continue

                # First cut the video to 21 seconds
                p1 = subprocess.call(['ffmpeg.exe',
                                      '-y',
                                      '-i', self.root_path + '/Videos/full_videos/' + video,
                                      '-crf', '18',
                                      '-ss', str(trim_start),
                                      '-t', str(cut_length),
                                      self.root_path + '/Videos/cut_videos/TEMP' + video])
                p2_vid_input = self.root_path + '/Videos/cut_videos/TEMP' + video

                video_fade, result_txt = self.timer_text_overlay_ffmpeg_input_strings(video.split('.mp4')[0])

                v_w, v_h = self.get_height_width(self.root_path + '/Videos/cut_videos/TEMP' + video)
                if v_w != 1280 or v_h != 720:
                    self.scale_video_width_height(video='TEMP'+video, path=self.root_path + '/Videos/cut_videos/',
                                                  scaling=scaling)

                if self.check_if_file_exists(self.root_path + '/Videos/cut_videos/resizedTEMP' + video):
                    p2_vid_input = self.root_path + '/Videos/cut_videos/resizedTEMP' + video

                # Add overlay to the first 10 seconds
                p2 = subprocess.call(["ffmpeg.exe",
                                      "-i", p2_vid_input,
                                      "-i", f'{self.countdown_overlay_path}/{self.countdown_overlay_name}',
                                      "-filter_complex", video_fade,
                                      "-shortest",
                                      "-map", "[out]",
                                      '-map', '0:1',
                                      '-crf', '18',
                                      '-c:a', 'aac',
                                      '-q:a', '1000',
                                      self.root_path + '/Videos/cut_videos/withvid' + video])

                # Add text result on top of video after the first 10s
                p3 = subprocess.call(["ffmpeg.exe",
                                      "-i",self.root_path + '/Videos/cut_videos/withvid' + video,
                                      "-vf", result_txt,
                                      "-codec:a", 'copy',
                                      self.root_path + '/Videos/cut_videos/' + video])

                # Delete all the temporary files
                for del_name in ['TEMP'+video, 'withvid'+video, 'resizedTEMP'+video]:
                    try:
                        os.remove(self.root_path+'/Videos/cut_videos/'+del_name)
                    except OSError:
                        pass

        if overlay_resized:
            os.remove(self.countdown_overlay_path + '/' + self.countdown_overlay_name)

    def concat_videos(self, n_concatenated):
        cut_video_path = self.root_path + '/Videos/cut_videos'
        list_of_videos = self.fetch_mp4_files(cut_video_path)
        with cwd(cut_video_path):
            clips = []
            for vid in list_of_videos:
                clip = VideoFileClip(vid)
                clip = (clip.fx(afx.audio_fadein, duration=1))
                clip = (clip.fx(afx.audio_fadeout, duration=1))
                clips.append(clip)
        result = concatenate_videoclips(clips)
        with cwd(path=self.root_path + '/Videos/complete_videos'):
            unique_name = len(self.fetch_mp4_files(path=os.getcwd()))
            if unique_name is None:
                unique_name = 0
            result.write_videofile(str(unique_name+1) + "_MusicQuiz.mp4", audio_bitrate='3000k', preset='veryfast')


if __name__ == '__main__':
    ffmpeg_dir = os.getcwd() + '/ffmpeg_folder'
    overlay_font_dir = os.getcwd() + '/font_and_overlay'

    MQC = MusicQuizCreator(ffmpeg_tools_path=ffmpeg_dir)
    MQC.download_youtube_video(txt_name='youtube_download_list.txt', txt_path=os.getcwd())
    MQC.cut_videos(countdown_overlay_name='Countdown.mp4', font_name='myfont.ttf',
                   countdown_overlay_path=overlay_font_dir, font_path=overlay_font_dir)
    MQC.concat_videos(n_concatenated=2)