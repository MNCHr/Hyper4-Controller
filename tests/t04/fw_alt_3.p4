header_type meta_t {
  fields {
    val : 96;
    is_dropped : 1;
  }
}

metadata meta_t meta;

action _drop() {
  modify_field(meta.isdropped, 1);
  drop();
}

action cond(val) {
  modify_field(meta.val, meta.val + val);
}

table ip_dst {
  reads {
    ip.dst : exact;
  }
  actions {
  _drop;
  _no_op;
  cond;
  }
}

table ip_src {
  reads {
    ip.src : exact;
  }
  actions {
  _drop;
  _no_op;
  cond;
  }
}

table l4_src {
  reads {
    l4.src : exact;
  }
  actions {
  _drop;
  _no_op;
  cond;
  }
}

table l4_src {
  reads {
    l4.src : exact;
  }
  actions {
  _drop;
  _no_op;
  cond;
  }
}

table is_dropped_already {
  reads {
    meta.is_dropped : exact;
  }
  actions {
    is_not_dropped_already;
    is_dropped_already;
  }
}

table final_drop {
  reads {
    meta.val : exact;
  }
  actions {
    _drop;
    _no_op;
  }
}

control ingress {
  apply(ip_dst);
  apply(ip_src);
  apply(l4_dst);
  apply(l4_src);
  apply(is_dropped_already) {
    is_not_dropped_already {
      apply(final_drop);
    }
  }
}
