import { useQuery, useMutation } from 'react-query';
import { useDispatch } from 'react-redux';
import { settingsApi } from '../api';
import { setSettings } from '../store/settingsSlice';
import type { UpdateSettingsDto } from '../types/settings';

export const useSettings = () => {
  const dispatch = useDispatch();

  const { data: settings, isLoading } = useQuery(
    'settings',
    settingsApi.getUserSettings
  );

  const { mutate: updateSettings } = useMutation(
    (data: UpdateSettingsDto) => settingsApi.updateSettings(data),
    {
      onSuccess: (response) => {
        dispatch(setSettings(response.data));
      }
    }
  );

  return {
    settings: settings?.data,
    isLoading,
    updateSettings
  };
};
