// src/components/forms/FileSourceForm.tsx
interface FileSourceFormData {
  files: FileList;
  validateOnly?: boolean;
}

export const FileSourceForm: React.FC = () => {
  const { upload, uploadProgress } = useFileSource();
  const { register, handleSubmit, formState: { errors } } = useForm<FileSourceFormData>();

  const onSubmit = (data: FileSourceFormData) => {
    upload(Array.from(data.files));
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Upload Files
        </label>
        <input
          type="file"
          multiple
          {...register('files', {
            required: 'Please select files to upload',
            validate: {
              fileType: (files) => {
                if (!files[0]) return true;
                const validTypes = ['csv', 'json', 'xlsx', 'parquet'];
                return Array.from(files).every(file =>
                  validTypes.includes(file.name.split('.').pop()?.toLowerCase() || '')
                ) || 'Invalid file type. Supported: CSV, JSON, XLSX, Parquet';
              }
            }
          })}
          className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
        {errors.files && (
          <p className="mt-1 text-sm text-red-600">{errors.files.message}</p>
        )}
      </div>

      {uploadProgress > 0 && (
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full"
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
      )}

      <button
        type="submit"
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
      >
        Upload Files
      </button>
    </form>
  );
};