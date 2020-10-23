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

    def add_timer_and_overlay(self):
        pass

    def cut_videos(self, countdown_overlay_name, font_name, countdown_overlay_path, font_path):
        video_list = self.fetch_mp4_files(self.root_path + '/Videos/full_videos/')
        cut_length = 21.5
        with cwd(self.ffmpeg_tools_path):
            for video in video_list:
                vid_duration = self.get_video_length(video, self.root_path + '/Videos/full_videos/')
                trim_start = random.uniform(cut_length, vid_duration)
                if self.check_if_file_exists(filename=self.root_path + '/Videos/full_videos/' + video):
                    print(f'Video: {video} has already been trimmed. Skipping..')
                    continue
                p = subprocess.call(['ffmpeg.exe',
                                     '-i', self.root_path + '/Videos/full_videos/' + video,
                                     '-crf', '18',
                                     '-ss', str(trim_start),
                                     '-t', str(cut_length),
                                     self.root_path + '/Videos/cut_videos/' + video])

# Test
#  Parser, to cut the downloaded videos
#  Add the overlay and text with result
#  Sitch videos together

if __name__ == '__main__':
    ffmpeg_dir = os.getcwd() + '/ffmpeg_folder'
    overlay_font_dir = os.getcwd() + '/font_and_overlay'

    MQC = MusicQuizCreator(ffmpeg_tools_path=ffmpeg_dir)
    #MQC.download_youtube_video(txt_name='youtube_download_list.txt', txt_path=os.getcwd())
    MQC.cut_videos(countdown_overlay_name='Countdown.mp4', font_name='myfont.ttf',
                   countdown_overlay_path=overlay_font_dir, font_path=overlay_font_dir)