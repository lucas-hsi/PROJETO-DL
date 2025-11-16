import React, { useState, useCallback } from 'react';
import styled from 'styled-components';
import { colors } from '@/styles/tokens';
import { Edit3, Save, X, Package, DollarSign, Box } from 'lucide-react';
import { apiPost } from '@/lib/api';


interface EditableProductRowProps {
  produto: {
    sku: string;
    titulo: string;
    preco: number;
    estoque: number;
    origem: string;
    status: string;
    descricao?: string;
  };
  onUpdate: (updatedProduto: any) => void;
  isEditing?: boolean;
  onEditStart?: () => void;
  onEditEnd?: () => void;
}

const Row = styled.tr<{ isEditing: boolean }>`
  background: ${props => props.isEditing ? '#f8fafc' : 'transparent'};
  transition: background-color 0.2s ease;
  
  &:hover {
    background: ${props => !props.isEditing ? '#f1f5f9' : '#f8fafc'};
  }
`;

const Cell = styled.td`
  padding: 16px 12px;
  vertical-align: middle;
  border-bottom: 1px solid #e5e7eb;
`;

const EditableCell = styled(Cell)<{ isEditing: boolean }>`
  position: relative;
  
  ${props => props.isEditing && `
    padding: 8px 12px;
  `}
`;

const EditButton = styled.button`
  background: none;
  border: none;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  color: ${colors.textLight};
  transition: all 0.2s ease;
  
  &:hover {
    background: #e5e7eb;
    color: ${colors.textDark};
  }
`;

const ActionButtons = styled.div`
  display: flex;
  gap: 4px;
  align-items: center;
`;

const Input = styled.input`
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #3b82f6;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  
  &:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #3b82f6;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  min-height: 60px;
  resize: vertical;
  
  &:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

const SaveButton = styled.button`
  background: #10b981;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  
  &:hover {
    background: #059669;
  }
  
  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
`;

const CancelButton = styled.button`
  background: #ef4444;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  
  &:hover {
    background: #dc2626;
  }
`;

const ProductInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const ProductTitle = styled.div`
  font-weight: 600;
  color: ${colors.textDark};
  line-height: 1.4;
`;

const ProductSKU = styled.div`
  font-size: 12px;
  color: ${colors.textLight};
  font-family: monospace;
`;

const PriceDisplay = styled.div`
  font-weight: 600;
  color: ${colors.textDark};
  font-size: 16px;
`;

const StockDisplay = styled.div<{ lowStock: boolean }>`
  font-weight: 600;
  color: ${props => props.lowStock ? '#dc2626' : '#16a34a'};
`;

const StatusBadge = styled.span<{ status: string }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  background: ${props => props.status === 'ATIVO' ? '#dcfce7' : '#f1f5f9'};
  color: ${props => props.status === 'ATIVO' ? '#166534' : '#4b5563'};
`;

export default function EditableProductRow({ 
  produto, 
  onUpdate, 
  isEditing: externalIsEditing,
  onEditStart,
  onEditEnd 
}: EditableProductRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    titulo: produto.titulo,
    preco: produto.preco,
    estoque: produto.estoque,
    descricao: produto.descricao || '',
  });
  const [isSaving, setIsSaving] = useState(false);

  const handleEdit = useCallback(() => {
    setIsEditing(true);
    setEditData({
      titulo: produto.titulo,
      preco: produto.preco,
      estoque: produto.estoque,
      descricao: produto.descricao || '',
    });
    onEditStart?.();
  }, [produto, onEditStart]);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    
    try {
      // Validar dados
      if (!editData.titulo.trim()) {
        console.error('Título é obrigatório');
        return;
      }
      
      if (editData.preco < 0) {
        console.error('Preço não pode ser negativo');
        return;
      }
      
      if (editData.estoque < 0) {
        console.error('Estoque não pode ser negativo');
        return;
      }

      // Enviar para API
      const response = await fetch(`/api/estoque/${produto.sku}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          titulo: editData.titulo.trim(),
          preco: parseFloat(editData.preco.toString()),
          estoque_atual: parseInt(editData.estoque.toString()),
          descricao: editData.descricao.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error('Erro ao salvar produto');
      }

      const updatedProduto = await response.json();
      
      // Atualizar estado local
      onUpdate(updatedProduto);
      setIsEditing(false);
      
      console.log('✅ Produto atualizado com sucesso!');
      onEditEnd?.();
      
    } catch (error) {
      console.error('Erro ao salvar produto:', error);
      console.error('❌ Erro ao salvar produto. Tente novamente.');
    } finally {
      setIsSaving(false);
    }
  }, [editData, produto.sku, onUpdate, onEditEnd]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditData({
      titulo: produto.titulo,
      preco: produto.preco,
      estoque: produto.estoque,
      descricao: produto.descricao || '',
    });
    onEditEnd?.();
  }, [produto, onEditEnd]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleCancel();
    } else if (e.key === 'Enter' && e.ctrlKey) {
      handleSave();
    }
  }, [handleCancel, handleSave]);

  const isLowStock = produto.estoque <= 5;

  return (
    <Row isEditing={isEditing} onKeyDown={handleKeyDown}>
      {/* Checkbox */}
      <Cell>
        <input type="checkbox" style={{ margin: 0 }} />
      </Cell>

      {/* Imagem */}
      <Cell>
        <div style={{ 
          width: '48px', 
          height: '48px', 
          background: '#f1f5f9', 
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px'
        }}>
          📦
        </div>
      </Cell>

      {/* Menu de ações */}
      <Cell>
        <ActionButtons>
          {!isEditing ? (
            <EditButton onClick={handleEdit} title="Editar produto">
              <Edit3 size={16} />
            </EditButton>
          ) : (
            <>
              <SaveButton onClick={handleSave} disabled={isSaving}>
                <Save size={16} />
                {isSaving ? 'Salvando...' : 'Salvar'}
              </SaveButton>
              <CancelButton onClick={handleCancel}>
                <X size={16} />
                Cancelar
              </CancelButton>
            </>
          )}
        </ActionButtons>
      </Cell>

      {/* Descrição / Título */}
      <Cell>
        {isEditing ? (
          <ProductInfo>
            <TextArea
              value={editData.titulo}
              onChange={(e) => setEditData({ ...editData, titulo: e.target.value })}
              placeholder="Título do produto"
              rows={2}
            />
          </ProductInfo>
        ) : (
          <ProductInfo>
            <ProductTitle>{produto.titulo}</ProductTitle>
            <ProductSKU>{produto.sku}</ProductSKU>
          </ProductInfo>
        )}
      </Cell>

      {/* Código SKU */}
      <Cell>
        <code style={{ 
          background: '#f1f5f9', 
          padding: '4px 8px', 
          borderRadius: '4px',
          fontSize: '12px',
          fontFamily: 'monospace'
        }}>
          {produto.sku}
        </code>
      </Cell>

      {/* Unidade */}
      <Cell>
        <span style={{ color: colors.textLight }}>UN</span>
      </Cell>

      {/* Preço */}
      <Cell>
        {isEditing ? (
          <div style={{ position: 'relative' }}>
            <DollarSign 
              size={16} 
              style={{ 
                position: 'absolute', 
                left: '12px', 
                top: '50%', 
                transform: 'translateY(-50%)',
                color: colors.textLight
              }} 
            />
            <Input
              type="number"
              step="0.01"
              min="0"
              value={editData.preco}
              onChange={(e) => setEditData({ ...editData, preco: parseFloat(e.target.value) || 0 })}
              style={{ paddingLeft: '36px' }}
            />
          </div>
        ) : (
          <PriceDisplay>R$ {produto.preco.toFixed(2)}</PriceDisplay>
        )}
      </Cell>

      {/* Estoque Físico */}
      <Cell>
        {isEditing ? (
          <div style={{ position: 'relative' }}>
            <Box 
              size={16} 
              style={{ 
                position: 'absolute', 
                left: '12px', 
                top: '50%', 
                transform: 'translateY(-50%)',
                color: colors.textLight
              }} 
            />
            <Input
              type="number"
              min="0"
              value={editData.estoque}
              onChange={(e) => setEditData({ ...editData, estoque: parseInt(e.target.value) || 0 })}
              style={{ paddingLeft: '36px' }}
            />
          </div>
        ) : (
          <StockDisplay lowStock={isLowStock}>
            {produto.estoque} un
          </StockDisplay>
        )}
      </Cell>

      {/* Estoque Disponível */}
      <Cell>
        <StockDisplay lowStock={isLowStock}>
          {produto.estoque} un
        </StockDisplay>
      </Cell>

      {/* Integrações */}
      <Cell>
        <div style={{ display: 'flex', gap: '8px' }}>
          {produto.origem === 'MERCADO_LIVRE' && (
            <span title="Mercado Livre" style={{ fontSize: '16px' }}>🟡</span>
          )}
          <span title="Shopify" style={{ fontSize: '16px' }}>🟢</span>
        </div>
      </Cell>

      {/* Ação */}
      <Cell>
        <div style={{ 
          width: '32px', 
          height: '32px', 
          background: '#f1f5f9', 
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'background 0.2s ease'
        }} 
        onClick={handleEdit}
        title="Ver detalhes"
        >
          <span style={{ color: colors.textLight }}>›</span>
        </div>
      </Cell>
    </Row>
  );
}