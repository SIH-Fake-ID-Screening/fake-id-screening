import { useRef, useState } from 'react';
import { Upload, X, CheckCircle2 } from 'lucide-react';

export default function FileUploadZone({ label, accept = 'image/*', onFile, file }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && onFile) onFile(f);
  };

  const handleChange = (e) => {
    const f = e.target.files[0];
    if (f && onFile) onFile(f);
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    if (onFile) onFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const preview = file ? URL.createObjectURL(file) : null;

  return (
    <div
      className={`upload-zone${dragging ? ' drag-over' : ''}${file ? ' has-file' : ''}`}
      onClick={() => !file && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={handleChange}
      />

      {file ? (
        <>
          {preview && <img src={preview} alt="preview" className="upload-preview" />}
          <div className="flex items-center gap-2 mt-2">
            <CheckCircle2 size={14} color="var(--success)" />
            <span style={{ fontSize: 12, color: 'var(--success)', fontWeight: 500 }}>
              {file.name.length > 30 ? file.name.slice(0, 28) + '…' : file.name}
            </span>
          </div>
          <button className="upload-remove" onClick={handleRemove}>
            <X size={12} />
          </button>
        </>
      ) : (
        <>
          <div className="upload-icon">
            <Upload size={28} />
          </div>
          <div className="upload-title">{label}</div>
          <div className="upload-hint">Drag & drop or click to browse</div>
          <div className="upload-hint">JPG, PNG — max 10 MB</div>
        </>
      )}
    </div>
  );
}
