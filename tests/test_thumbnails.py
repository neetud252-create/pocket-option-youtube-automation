import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import youtube
from googleapiclient.errors import HttpError


class ThumbnailTests(unittest.TestCase):
    def test_extracts_at_two_seconds_and_checks_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / 'frame.jpg')
            def render(command, **kwargs):
                self.assertEqual(command[command.index('-ss') + 1], '2.000')
                self.assertLess(command.index('-i'), command.index('-ss'))
                Path(output).write_bytes(b'jpeg')
            with patch.object(youtube.subprocess, 'run', side_effect=render):
                youtube.extract_thumbnail('final.mp4', output)
            os.remove(output)
            with patch.object(youtube.subprocess, 'run'):
                with self.assertRaises(RuntimeError):
                    youtube.extract_thumbnail('final.mp4', output)

    def test_thumbnail_failure_preserves_uploaded_id_and_records_failure(self):
        service = Mock()
        service.videos.return_value.insert.return_value.next_chunk.return_value = (None, {'id': 'uploaded'})
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / 'short.mp4'
            video.write_bytes(b'video')
            with patch.object(youtube, 'MediaFileUpload'), patch.object(youtube, 'DATA_DIR', directory), patch.object(youtube, 'get_youtube_service', return_value=service), patch.object(youtube, 'extract_thumbnail'), patch.object(youtube, 'set_short_thumbnail', side_effect=RuntimeError('not eligible')):
                result = youtube._upload_video(str(video), 'title', 'description', 'private', channel='goplustrader')
                self.assertEqual(result['video_id'], 'uploaded')
                self.assertEqual(youtube.get_thumbnail_status('uploaded')['status'], 'failed')
                service.videos.return_value.insert.assert_called_once()

    def test_success_records_timestamp_and_cleans_up_image(self):
        with tempfile.TemporaryDirectory() as directory:
            image_paths = []
            def render(video, path):
                Path(path).write_bytes(b'jpeg')
                image_paths.append(path)
            with patch.object(youtube, 'DATA_DIR', directory), patch.object(youtube, 'extract_thumbnail', side_effect=render), patch.object(youtube, 'set_short_thumbnail') as upload:
                status = youtube.apply_short_thumbnail(Mock(), 'video', 'final.mp4')
                self.assertEqual(status, {'timestamp_seconds': 2.0, 'status': 'set'})
                self.assertEqual(youtube.get_thumbnail_status('video'), status)
                self.assertEqual(upload.call_args.args[1], 'video')
            self.assertFalse(Path(image_paths[0]).exists())

    def test_retries_only_thumbnail_for_transient_failure(self):
        service = Mock()
        error = HttpError(Mock(status=503, reason='unavailable'), b'{}')
        service.thumbnails.return_value.set.return_value.execute.side_effect = [error, {'items': [{}]}]
        with patch.object(youtube, 'MediaFileUpload'), patch.object(youtube.time, 'sleep'):
            youtube.set_short_thumbnail(service, 'video', 'frame.jpg')
        self.assertEqual(service.thumbnails.return_value.set.call_count, 2)
        service.videos.assert_not_called()


if __name__ == '__main__':
    unittest.main()
