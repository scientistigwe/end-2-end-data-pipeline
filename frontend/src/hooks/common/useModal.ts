// src/hooks/useModal.ts
import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { openModal, closeModal } from '../store/slices/uiSlice';
import { selectModalState } from '../store/selectors/uiSelectors';

interface UseModalProps {
  modalId: string;
  onOpen?: () => void;
  onClose?: () => void;
}

export const useModal = ({ modalId, onOpen, onClose }: UseModalProps) => {
  const dispatch = useDispatch();
  const { isOpen, data } = useSelector(selectModalState(modalId));

  const open = useCallback((modalData?: any) => {
    dispatch(openModal({ modalId, data: modalData }));
    onOpen?.();
  }, [dispatch, modalId, onOpen]);

  const close = useCallback(() => {
    dispatch(closeModal(modalId));
    onClose?.();
  }, [dispatch, modalId, onClose]);

  return {
    isOpen,
    data,
    open,
    close
  };
};
