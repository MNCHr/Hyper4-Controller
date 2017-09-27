table ip_dst {
  reads {
    ip.dst : exact;
  }
  actions {
    _no_op;
    _drop;
    cond;
  }
}

table ip_src_1 {
  reads {
    ip.src : exact;
  }
  actions {
    _no_op;
    _drop;
    cond;
  }
}

table ip_src_1 {
  reads {
    ip.src : exact;
  }
  actions {
    _no_op;
    _drop;
    cond;
  }
}

/*
   This doesn't work because the effect is that for all '&&' style firewall rules,
   we have all the left-side operands grouped together combining with any of the
   right-side operands.  I don't see how to match on just a single field and
   support complex firewall rules.
*/
control ingress {
  apply(ip_dst) {
    _no_op {
      apply(ip_src_1) {
        _no_op {
          apply(l4_dst_1) {
            _no_op {
              apply(l4_src_1);
            }
            cond {
              apply(l4_src_2);
            }
          }
        }
        cond {
          apply(l4_dst_2) {
            _no_op {
              apply(l4_src_3);
            }
            cond {
              apply(l4_src_4);
            }
          }
        }
      }
    }
    cond {
      apply(ip_src_2) {
        _no_op {
          apply(l4_dst_3) {
            _no_op {
              apply(l4_src_5);
            }
            cond {
              apply(l4_src_6);
            }
          }
        }
        cond {
          apply(l4_dst_4) {
            _no_op {
              apply(l4_src_7);
            }
            cond {
              apply(l4_src_8);
            }
          }
        }
      }
    }
  }
}

/*
table_set_default ip_dst _no_op
table_set_default ip_src_standalone _no_op
table_set_default ip_src_cond _no_op
*/
