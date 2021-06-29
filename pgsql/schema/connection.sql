drop table if exists connection;

create table if not exists connection (
	id serial primary key,
	xid char(32) not null,
	user_xid char(32) not null,
	"type" varchar(16) not null,
	name varchar(32) not null,
	configuration text not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
