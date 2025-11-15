import React from 'react';
import { motion } from 'framer-motion';
import PainelLayout from '@/components/layout/PainelLayout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import styled from 'styled-components';
import { colors } from '@/styles/tokens';

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
`;

export default function DashboardGestor() {
  return (
    <PainelLayout titulo="Dashboard" tipoUsuario="gestor">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Visão Geral</CardTitle>
              <CardDescription>Indicadores consolidados do sistema</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Grid>
              <div>
                <div style={{ color: colors.textLight, fontSize: 12 }}>Produtos</div>
                <div style={{ color: colors.textDark, fontSize: 24, fontWeight: 700 }}>—</div>
              </div>
              <div>
                <div style={{ color: colors.textLight, fontSize: 12 }}>Anúncios</div>
                <div style={{ color: colors.textDark, fontSize: 24, fontWeight: 700 }}>—</div>
              </div>
              <div>
                <div style={{ color: colors.textLight, fontSize: 12 }}>Sincronizações</div>
                <div style={{ color: colors.textDark, fontSize: 24, fontWeight: 700 }}>—</div>
              </div>
            </Grid>
          </CardContent>
        </Card>
      </motion.div>
    </PainelLayout>
  );
}