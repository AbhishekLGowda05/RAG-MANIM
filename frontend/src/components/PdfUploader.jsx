import React, { useState, useRef } from 'react';
import { Upload, File, CheckCircle, AlertCircle, Loader } from 'lucide-react';

export default function PdfUploader({ onUploadComplete }) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, uploading, indexing, success, error
  const [message, setMessage] = useState('');
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (selectedFile) => {
    if (selectedFile.type !== 'application/pdf') {
      setStatus('error');
      setMessage('Please upload a valid PDF file.');
      return;
    }
    setFile(selectedFile);
    setStatus('idle');
    setMessage('');
  };

  const onButtonClick = () => {
    inputRef.current.click();
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setStatus('uploading');
    setMessage('Uploading textbook...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      // 1. Upload
      const uploadRes = await fetch('http://localhost:8000/api/curriculum/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!uploadRes.ok) throw new Error('Upload failed');
      const uploadData = await uploadRes.json();
      
      // 2. Index
      setStatus('indexing');
      setMessage('Extracting chapters, generating structure, and building concept graph... (this may take a few minutes)');
      
      const indexRes = await fetch(`http://localhost:8000/api/curriculum/index/${uploadData.document_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: uploadData.path }),
      });
      
      if (!indexRes.ok) throw new Error('Indexing failed');
      
      setStatus('success');
      setMessage('Textbook successfully indexed and curriculum graph generated!');
      
      if (onUploadComplete) {
        onUploadComplete();
      }
      
      // Reset after 3 seconds
      setTimeout(() => {
        setFile(null);
        setStatus('idle');
        setMessage('');
      }, 3000);
      
    } catch (err) {
      setStatus('error');
      setMessage(err.message || 'An error occurred during upload/indexing.');
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-2xl relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>
      
      <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
        <Upload className="w-5 h-5 mr-2 text-indigo-400" />
        Ingest New Curriculum
      </h2>
      
      {!file ? (
        <form 
          className={`border-2 border-dashed rounded-lg p-10 text-center transition-all ${
            dragActive ? 'border-indigo-500 bg-indigo-500/10' : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={onButtonClick}
        >
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept="application/pdf"
            onChange={handleChange}
          />
          <File className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-300 font-medium mb-1">Drag and drop your textbook PDF here</p>
          <p className="text-gray-500 text-sm">or click to browse files</p>
        </form>
      ) : (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 flex items-center justify-between">
          <div className="flex items-center">
            <File className="w-8 h-8 text-indigo-400 mr-3" />
            <div>
              <p className="text-white font-medium truncate max-w-[200px] md:max-w-xs">{file.name}</p>
              <p className="text-gray-400 text-xs">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
          </div>
          
          {status === 'idle' && (
            <div className="flex gap-2">
              <button 
                onClick={() => setFile(null)}
                className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={handleUpload}
                className="px-4 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-md font-medium transition-colors"
              >
                Process PDF
              </button>
            </div>
          )}
        </div>
      )}

      {status !== 'idle' && status !== 'error' && (
        <div className="mt-4 p-4 rounded-lg bg-gray-800/80 border border-gray-700 flex items-center">
          {status === 'success' ? (
            <CheckCircle className="w-6 h-6 text-green-400 mr-3 shrink-0" />
          ) : (
            <Loader className="w-6 h-6 text-indigo-400 mr-3 shrink-0 animate-spin" />
          )}
          <div className="flex-1">
            <p className={`text-sm font-medium ${status === 'success' ? 'text-green-400' : 'text-indigo-300'}`}>
              {status === 'uploading' && 'Uploading...'}
              {status === 'indexing' && 'Building Semantic Layer...'}
              {status === 'success' && 'Complete!'}
            </p>
            <p className="text-gray-400 text-xs mt-1">{message}</p>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="mt-4 p-4 rounded-lg bg-red-900/20 border border-red-900/50 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-400 mr-2 shrink-0 mt-0.5" />
          <p className="text-red-300 text-sm">{message}</p>
        </div>
      )}
    </div>
  );
}
