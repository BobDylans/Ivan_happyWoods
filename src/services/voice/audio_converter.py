"""
音频格式转换工具

支持将常见音频格式（MP3, WAV, M4A, AAC, OGG, FLAC等）转换为PCM格式。
使用 pydub 库进行音频处理，底层依赖 ffmpeg。
"""

import logging
import io
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioConverter:
    """
    音频格式转换器
    
    支持的输入格式:
    - MP3
    - WAV
    - M4A (AAC)
    - AAC
    - OGG
    - FLAC
    - WEBM
    - AMR
    
    输出格式:
    - PCM (16kHz, 16-bit, mono)
    """
    
    # 支持的音频格式
    SUPPORTED_FORMATS = {
        '.mp3', '.wav', '.m4a', '.aac', '.ogg', 
        '.flac', '.webm', '.amr', '.wma', '.opus'
    }
    
    # 目标PCM参数
    TARGET_SAMPLE_RATE = 16000  # 16kHz
    TARGET_CHANNELS = 1          # 单声道
    TARGET_SAMPLE_WIDTH = 2      # 16-bit (2 bytes)
    
    def __init__(self):
        """初始化转换器，检查依赖"""
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查依赖库是否可用"""
        try:
            from pydub import AudioSegment
            from pydub.utils import which
            
            # 检查 ffmpeg 是否可用
            if not which("ffmpeg") and not which("avconv"):
                logger.warning(
                    "ffmpeg/avconv 未找到。某些音频格式可能无法转换。\n"
                    "请安装 ffmpeg: https://ffmpeg.org/download.html"
                )
            
            self._audio_segment = AudioSegment
            logger.info("音频转换器初始化成功")
            
        except ImportError as e:
            logger.error(
                f"pydub 库未安装: {e}\n"
                "请运行: pip install pydub"
            )
            raise
    
    def is_supported_format(self, filename: str) -> bool:
        """
        检查文件格式是否支持
        
        Args:
            filename: 文件名
            
        Returns:
            是否支持该格式
        """
        suffix = Path(filename).suffix.lower()
        return suffix in self.SUPPORTED_FORMATS or suffix == '.pcm'
    
    def detect_format(self, filename: str, content: bytes) -> str:
        """
        检测音频格式
        
        Args:
            filename: 文件名
            content: 文件内容（前几个字节）
            
        Returns:
            格式名称 (mp3/wav/m4a/pcm等)
        """
        # 1. 先根据文件名判断
        suffix = Path(filename).suffix.lower().lstrip('.')
        
        # 2. 如果文件名不可靠，通过文件头判断
        if len(content) >= 12:
            # WAV: RIFF....WAVE
            if content[:4] == b'RIFF' and content[8:12] == b'WAVE':
                return 'wav'
            
            # MP3: ID3 或 0xFF 0xFB
            if content[:3] == b'ID3' or (content[0] == 0xFF and content[1] & 0xE0 == 0xE0):
                return 'mp3'
            
            # M4A/AAC: ftyp
            if b'ftyp' in content[:16]:
                return 'm4a'
            
            # OGG: OggS
            if content[:4] == b'OggS':
                return 'ogg'
            
            # FLAC: fLaC
            if content[:4] == b'fLaC':
                return 'flac'
        
        # 3. 如果都检测不到，使用文件名后缀
        return suffix if suffix else 'unknown'
    
    def convert_to_pcm(
        self, 
        audio_data: bytes, 
        source_format: Optional[str] = None
    ) -> Tuple[bytes, dict]:
        """
        将音频转换为PCM格式
        
        Args:
            audio_data: 原始音频数据
            source_format: 源格式 (mp3/wav/m4a等)，如果为None则自动检测
            
        Returns:
            (pcm_data, info)
            - pcm_data: PCM音频数据
            - info: 转换信息 {
                'source_format': 源格式,
                'source_duration': 原始时长(秒),
                'source_sample_rate': 原始采样率,
                'source_channels': 原始声道数,
                'converted': 是否进行了转换,
                'target_sample_rate': 目标采样率,
                'target_channels': 目标声道数
              }
        """
        from pydub import AudioSegment
        
        try:
            # 自动检测格式
            if source_format is None:
                source_format = self.detect_format('', audio_data)
            
            logger.info(f"音频格式检测: {source_format}")
            
            # 如果已经是原始PCM，直接返回
            if source_format == 'pcm' or source_format == 'raw':
                return audio_data, {
                    'source_format': 'pcm',
                    'source_duration': len(audio_data) / (self.TARGET_SAMPLE_RATE * self.TARGET_SAMPLE_WIDTH),
                    'source_sample_rate': self.TARGET_SAMPLE_RATE,
                    'source_channels': self.TARGET_CHANNELS,
                    'converted': False,
                    'target_sample_rate': self.TARGET_SAMPLE_RATE,
                    'target_channels': self.TARGET_CHANNELS
                }
            
            # 加载音频文件
            logger.info(f"开始加载 {source_format} 格式音频...")
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data), 
                format=source_format
            )
            
            # 记录原始信息
            source_info = {
                'source_format': source_format,
                'source_duration': len(audio) / 1000.0,  # pydub使用毫秒
                'source_sample_rate': audio.frame_rate,
                'source_channels': audio.channels,
                'source_sample_width': audio.sample_width
            }
            
            logger.info(
                f"原始音频: {source_info['source_sample_rate']}Hz, "
                f"{source_info['source_channels']}声道, "
                f"{source_info['source_sample_width']*8}bit, "
                f"{source_info['source_duration']:.2f}秒"
            )
            
            # 转换到目标格式
            # 1. 设置采样率
            if audio.frame_rate != self.TARGET_SAMPLE_RATE:
                logger.info(f"重采样: {audio.frame_rate}Hz -> {self.TARGET_SAMPLE_RATE}Hz")
                audio = audio.set_frame_rate(self.TARGET_SAMPLE_RATE)
            
            # 2. 转换为单声道
            if audio.channels != self.TARGET_CHANNELS:
                logger.info(f"转换声道: {audio.channels} -> {self.TARGET_CHANNELS}")
                audio = audio.set_channels(self.TARGET_CHANNELS)
            
            # 3. 设置采样宽度为16-bit
            if audio.sample_width != self.TARGET_SAMPLE_WIDTH:
                logger.info(f"转换位深: {audio.sample_width*8}bit -> {self.TARGET_SAMPLE_WIDTH*8}bit")
                audio = audio.set_sample_width(self.TARGET_SAMPLE_WIDTH)
            
            # 导出为原始PCM数据
            pcm_data = audio.raw_data
            
            logger.info(
                f"转换完成: PCM {self.TARGET_SAMPLE_RATE}Hz, "
                f"{self.TARGET_CHANNELS}声道, 16bit, "
                f"{len(pcm_data)} bytes"
            )
            
            return pcm_data, {
                **source_info,
                'converted': True,
                'target_sample_rate': self.TARGET_SAMPLE_RATE,
                'target_channels': self.TARGET_CHANNELS,
                'target_sample_width': self.TARGET_SAMPLE_WIDTH,
                'output_size': len(pcm_data)
            }
            
        except Exception as e:
            logger.error(f"音频转换失败: {e}", exc_info=True)
            raise AudioConversionError(f"音频转换失败: {str(e)}") from e
    
    def validate_audio(self, pcm_data: bytes) -> Tuple[bool, str]:
        """
        验证PCM音频数据
        
        Args:
            pcm_data: PCM音频数据
            
        Returns:
            (is_valid, message)
        """
        # 检查大小
        min_size = self.TARGET_SAMPLE_RATE * self.TARGET_SAMPLE_WIDTH * 0.1  # 至少0.1秒
        if len(pcm_data) < min_size:
            return False, f"音频过短: {len(pcm_data)} bytes (最小 {min_size} bytes)"
        
        max_size = 10 * 1024 * 1024  # 10MB
        if len(pcm_data) > max_size:
            return False, f"音频过大: {len(pcm_data)} bytes (最大 {max_size} bytes)"
        
        # 检查时长
        duration = len(pcm_data) / (self.TARGET_SAMPLE_RATE * self.TARGET_SAMPLE_WIDTH)
        max_duration = 60  # 60秒
        if duration > max_duration:
            return False, f"音频过长: {duration:.2f}秒 (最大 {max_duration}秒)"
        
        return True, "验证通过"


class AudioConversionError(Exception):
    """音频转换异常"""
    pass


# 全局转换器实例（单例）
_converter: Optional[AudioConverter] = None


def get_audio_converter() -> AudioConverter:
    """获取音频转换器实例（单例）"""
    global _converter
    
    if _converter is None:
        _converter = AudioConverter()
    
    return _converter
