drop table if exists connection cascade;

create table if not exists connection (
	xid char(32) primary key,
	user_xid char(32) not null,
	"type" varchar(16) not null,
	name varchar(32) not null,
	configuration text not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp,
	foreign key(user_xid) references "user"(xid)
);
