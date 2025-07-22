'use client';

import { useState, useRef } from 'react';

function ImageUploader() {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const fileInputRef = useRef(null);

  // 处理文件选择
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // 验证文件类型
    if (!file.type.match('image/(jpeg|png|gif|webp)')) {
      setUploadMessage('请选择图片文件 (JPEG, PNG, GIF, WEBP)');
      return;
    }

    // 验证文件大小 (2MB)
    if (file.size > 2 * 1024 * 1024) {
      setUploadMessage('文件大小不能超过 2MB');
      return;
    }

    // 创建预览图
    const reader = new FileReader();
    reader.onload = () => setPreviewUrl(reader.result);
    reader.readAsDataURL(file);
  };

  // 上传图片
  const uploadImage = async () => {
    if (!fileInputRef.current.files.length) {
      setUploadMessage('请选择图片');
      return;
    }

    const file = fileInputRef.current.files[0];
    const formData = new FormData();
    formData.append('image', file);
    formData.append('userId', '123'); // 附加其他数据

    setIsUploading(true);
    setUploadMessage('');

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
        // 不要设置 Content-Type! 浏览器会自动添加 "multipart/form-data"
      });

      const result = await response.json();
      
      if (!response.ok) throw new Error(result.error);
      
      setUploadMessage('✅ 上传成功!');
      console.log('图片 URL:', result.url);
      
      // 重置预览 (可选)
      setTimeout(() => {
        setPreviewUrl(null);
        fileInputRef.current.value = ''; // 重置文件输入
      }, 2000);
    } catch (error) {
      setUploadMessage(`❌ 上传失败: ${error.message}`);
      console.error('上传错误:', error);
    } finally {
      setIsUploading(false);
    }
  };

  // 打开文件选择器
  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="image-uploader">
      <input
        type="file"
        accept="image/*"
        ref={fileInputRef}
        onChange={handleFileChange}
        hidden
      />
      
      {/* 文件选择和预览区 */}
      <div 
        className={`upload-area ${previewUrl ? 'has-image' : ''}`}
        onClick={triggerFileInput}
      >
        {previewUrl ? (
          <img 
            src={previewUrl} 
            alt="预览" 
            className="preview-image"
            onClick={(e) => e.stopPropagation()} // 防止点击图片触发文件选择
          />
        ) : (
          <div className="upload-prompt">
            <span>点击或拖放图片到此处</span>
            <p>支持 JPG, PNG, GIF (最多 2MB)</p>
          </div>
        )}
      </div>
      
      {/* 操作按钮 */}
      <div className="controls">
        <button 
          onClick={triggerFileInput}
          className="secondary-btn"
        >
          选择其他图片
        </button>
        <button 
          onClick={uploadImage} 
          disabled={isUploading || !previewUrl}
          className="primary-btn"
        >
          {isUploading ? '上传中...' : '上传图片'}
        </button>
      </div>
      
      {/* 状态信息 */}
      {uploadMessage && (
        <div className={`message ${uploadMessage.includes('✅') ? 'success' : 'error'}`}>
          {uploadMessage}
        </div>
      )}
    </div>
  );
}

export default ImageUploader;