// src/common/hooks/useModal.ts
import { useCallback } from 'react';
import { useDispatch } from 'react-redux';
import type { Modal } from '../types/ui';
import { openModal, closeModal } from '../store/ui/uiSlice';

interface UseModalProps {
  id: string;
  onOpen?: () => void;
  onClose?: () => void;
}

export function useModal({ id, onOpen, onClose }: UseModalProps) {
  const dispatch = useDispatch();

  const open = useCallback((props?: Modal['props']) => {
    // Notice we're omitting the id here as it's handled by the slice
    const modalData: Omit<Modal, 'id'> = {
      type: 'default',
      props
    };
    dispatch(openModal(modalData));
    onOpen?.();
  }, [dispatch, onOpen]);

  const close = useCallback(() => {
    dispatch(closeModal(id));
    onClose?.();
  }, [dispatch, id, onClose]);

  return {
    open,
    isOpen: true,
    close
  };
}